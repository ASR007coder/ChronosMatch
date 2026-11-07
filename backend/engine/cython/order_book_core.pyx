# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: initializedcheck=False

"""Native order book: red-black price indexes and FIFO linked lists."""

from libc.stdlib cimport malloc, free
from libc.stdint cimport int64_t

INT64_MIN = -(2**63)
INT64_MAX = (2**63) - 1


def _validate_int64(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{name} must be an int, got {value!r}")
    if value < INT64_MIN or value > INT64_MAX:
        raise ValueError(f"{name} must fit in signed 64-bit range, got {value!r}")


cdef inline bint _is_black(PriceNode* node) noexcept:
    return node == NULL or not node.is_red


cdef void _collect_prices(PriceNode* node, list result):
    if node == NULL:
        return
    _collect_prices(node.left, result)
    result.append(node.price)
    _collect_prices(node.right, result)


cdef int _validate_subtree(
    PriceNode* node,
    PriceNode* expected_parent,
    PriceNode* lower,
    PriceNode* upper,
    Py_ssize_t* count
) except -1:
    cdef int left_height
    cdef int right_height
    if node == NULL:
        return 1
    if node.parent != expected_parent:
        raise AssertionError("Invalid parent pointer")
    if lower != NULL and node.price <= lower.price:
        raise AssertionError("BST ordering violation: lower bound")
    if upper != NULL and node.price >= upper.price:
        raise AssertionError("BST ordering violation: upper bound")
    if node.is_red:
        if node.left != NULL and node.left.is_red:
            raise AssertionError("Red node has red left child")
        if node.right != NULL and node.right.is_red:
            raise AssertionError("Red node has red right child")
    count[0] += 1
    left_height = _validate_subtree(node.left, node, lower, node, count)
    right_height = _validate_subtree(node.right, node, node, upper, count)
    if left_height != right_height:
        raise AssertionError("Black height mismatch")
    return left_height + (0 if node.is_red else 1)


cdef class CythonOrderBookSide:
    def __cinit__(self, bint is_bid):
        self.root = NULL
        self.best = NULL
        self.level_count = 0
        self.is_bid = is_bid

    def __dealloc__(self):
        self._free_tree(self.root)
        self.root = NULL
        self.best = NULL
        self.level_count = 0

    cdef void _free_tree(self, PriceNode* node) noexcept:
        cdef OrderNode* current
        cdef OrderNode* following
        if node == NULL:
            return
        self._free_tree(node.left)
        self._free_tree(node.right)
        current = node.head
        while current != NULL:
            following = current.next
            free(current)
            current = following
        free(node)

    cdef PriceNode* _find_price_c(self, int64_t price) noexcept:
        cdef PriceNode* current = self.root
        while current != NULL:
            if price == current.price:
                return current
            if price < current.price:
                current = current.left
            else:
                current = current.right
        return NULL

    cdef void _left_rotate(self, PriceNode* node) noexcept:
        cdef PriceNode* pivot = node.right
        node.right = pivot.left
        if pivot.left != NULL:
            pivot.left.parent = node
        pivot.parent = node.parent
        if node.parent == NULL:
            self.root = pivot
        elif node == node.parent.left:
            node.parent.left = pivot
        else:
            node.parent.right = pivot
        pivot.left = node
        node.parent = pivot

    cdef void _right_rotate(self, PriceNode* node) noexcept:
        cdef PriceNode* pivot = node.left
        node.left = pivot.right
        if pivot.right != NULL:
            pivot.right.parent = node
        pivot.parent = node.parent
        if node.parent == NULL:
            self.root = pivot
        elif node == node.parent.right:
            node.parent.right = pivot
        else:
            node.parent.left = pivot
        pivot.right = node
        node.parent = pivot

    cdef void _insert_fixup(self, PriceNode* node) noexcept:
        cdef PriceNode* parent
        cdef PriceNode* grandparent
        cdef PriceNode* uncle
        while node != self.root and node.parent.is_red:
            parent = node.parent
            grandparent = parent.parent
            if parent == grandparent.left:
                uncle = grandparent.right
                if uncle != NULL and uncle.is_red:
                    parent.is_red = False
                    uncle.is_red = False
                    grandparent.is_red = True
                    node = grandparent
                else:
                    if node == parent.right:
                        node = parent
                        self._left_rotate(node)
                        parent = node.parent
                        grandparent = parent.parent
                    parent.is_red = False
                    grandparent.is_red = True
                    self._right_rotate(grandparent)
            else:
                uncle = grandparent.left
                if uncle != NULL and uncle.is_red:
                    parent.is_red = False
                    uncle.is_red = False
                    grandparent.is_red = True
                    node = grandparent
                else:
                    if node == parent.left:
                        node = parent
                        self._right_rotate(node)
                        parent = node.parent
                        grandparent = parent.parent
                    parent.is_red = False
                    grandparent.is_red = True
                    self._left_rotate(grandparent)
        self.root.is_red = False

    cdef PriceNode* _insert_price_c(self, int64_t price) except NULL:
        cdef PriceNode* parent = NULL
        cdef PriceNode* current = self.root
        cdef PriceNode* node
        while current != NULL:
            parent = current
            if price == current.price:
                return current
            if price < current.price:
                current = current.left
            else:
                current = current.right
        node = <PriceNode*>malloc(sizeof(PriceNode))
        if node == NULL:
            raise MemoryError()
        node.price = price
        node.left = NULL
        node.right = NULL
        node.parent = parent
        node.is_red = True
        node.head = NULL
        node.tail = NULL
        node.order_count = 0
        if parent == NULL:
            self.root = node
        elif price < parent.price:
            parent.left = node
        else:
            parent.right = node
        self.level_count += 1
        if self.best == NULL:
            self.best = node
        elif self.is_bid and price > self.best.price:
            self.best = node
        elif not self.is_bid and price < self.best.price:
            self.best = node
        self._insert_fixup(node)
        return node

    cdef void _transplant_c(self, PriceNode* old_node, PriceNode* new_node) noexcept:
        if old_node.parent == NULL:
            self.root = new_node
        elif old_node == old_node.parent.left:
            old_node.parent.left = new_node
        else:
            old_node.parent.right = new_node
        if new_node != NULL:
            new_node.parent = old_node.parent

    cdef void _delete_fixup_c(self, PriceNode* node, PriceNode* parent) noexcept:
        cdef PriceNode* sibling
        while node != self.root and _is_black(node):
            if parent == NULL:
                break
            if node == parent.left:
                sibling = parent.right
                if sibling != NULL and sibling.is_red:
                    sibling.is_red = False
                    parent.is_red = True
                    self._left_rotate(parent)
                    sibling = parent.right
                if sibling == NULL:
                    node = parent
                    parent = node.parent
                elif _is_black(sibling.left) and _is_black(sibling.right):
                    sibling.is_red = True
                    node = parent
                    parent = node.parent
                else:
                    if _is_black(sibling.right):
                        if sibling.left != NULL:
                            sibling.left.is_red = False
                        sibling.is_red = True
                        self._right_rotate(sibling)
                        sibling = parent.right
                    sibling.is_red = parent.is_red
                    parent.is_red = False
                    if sibling.right != NULL:
                        sibling.right.is_red = False
                    self._left_rotate(parent)
                    node = self.root
                    parent = NULL
            else:
                sibling = parent.left
                if sibling != NULL and sibling.is_red:
                    sibling.is_red = False
                    parent.is_red = True
                    self._right_rotate(parent)
                    sibling = parent.left
                if sibling == NULL:
                    node = parent
                    parent = node.parent
                elif _is_black(sibling.left) and _is_black(sibling.right):
                    sibling.is_red = True
                    node = parent
                    parent = node.parent
                else:
                    if _is_black(sibling.left):
                        if sibling.right != NULL:
                            sibling.right.is_red = False
                        sibling.is_red = True
                        self._left_rotate(sibling)
                        sibling = parent.left
                    sibling.is_red = parent.is_red
                    parent.is_red = False
                    if sibling.left != NULL:
                        sibling.left.is_red = False
                    self._right_rotate(parent)
                    node = self.root
                    parent = NULL
        if node != NULL:
            node.is_red = False

    cdef void _recompute_best_c(self) noexcept:
        cdef PriceNode* current = self.root
        if current == NULL:
            self.best = NULL
            return
        if self.is_bid:
            while current.right != NULL:
                current = current.right
        else:
            while current.left != NULL:
                current = current.left
        self.best = current

    cdef void _delete_node_c(self, PriceNode* target) noexcept:
        cdef PriceNode* moved = target
        cdef PriceNode* child
        cdef PriceNode* child_parent
        cdef bint moved_was_red = moved.is_red
        if target.left == NULL:
            child = target.right
            child_parent = target.parent
            self._transplant_c(target, target.right)
            if child != NULL:
                child_parent = child.parent
        elif target.right == NULL:
            child = target.left
            child_parent = target.parent
            self._transplant_c(target, target.left)
            if child != NULL:
                child_parent = child.parent
        else:
            moved = target.right
            while moved.left != NULL:
                moved = moved.left
            moved_was_red = moved.is_red
            child = moved.right
            if moved.parent == target:
                child_parent = moved
                if child != NULL:
                    child.parent = moved
            else:
                child_parent = moved.parent
                self._transplant_c(moved, moved.right)
                moved.right = target.right
                moved.right.parent = moved
            self._transplant_c(target, moved)
            moved.left = target.left
            moved.left.parent = moved
            moved.is_red = target.is_red
        if not moved_was_red:
            self._delete_fixup_c(child, child_parent)
        free(target)
        self.level_count -= 1
        self._recompute_best_c()

    cdef int _append_order_c(self, int64_t price, int64_t order_id, int64_t quantity) except -1:
        cdef PriceNode* level
        cdef OrderNode* order
        if price <= 0:
            raise ValueError("price must be positive")
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        order = <OrderNode*>malloc(sizeof(OrderNode))
        if order == NULL:
            raise MemoryError()
        order.order_id = order_id
        order.quantity = quantity
        order.next = NULL
        try:
            level = self._find_price_c(price)
            if level == NULL:
                level = self._insert_price_c(price)
        except:
            free(order)
            raise
        if level.tail == NULL:
            level.head = order
            level.tail = order
        else:
            level.tail.next = order
            level.tail = order
        level.order_count += 1
        return 0

    cdef void _peek_order_c(self, int64_t price, int64_t* order_id, int64_t* quantity) except *:
        cdef PriceNode* level = self._find_price_c(price)
        if level == NULL or level.head == NULL:
            raise IndexError("peek from empty price level")
        order_id[0] = level.head.order_id
        quantity[0] = level.head.quantity

    cdef void _pop_order_c(self, int64_t price, int64_t* order_id, int64_t* quantity) except *:
        cdef PriceNode* level = self._find_price_c(price)
        cdef OrderNode* order
        if level == NULL or level.head == NULL:
            raise IndexError("pop from empty price level")
        order = level.head
        order_id[0] = order.order_id
        quantity[0] = order.quantity
        level.head = order.next
        if level.head == NULL:
            level.tail = NULL
        level.order_count -= 1
        free(order)
        if level.head == NULL:
            self._delete_node_c(level)

    cdef void _update_front_quantity_c(self, int64_t price, int64_t quantity) except *:
        cdef PriceNode* level = self._find_price_c(price)
        if level == NULL or level.head == NULL:
            raise IndexError("update on empty price level")
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        level.head.quantity = quantity

    cdef bint _has_best_c(self) noexcept:
        return self.best != NULL

    cdef int64_t _best_price_c(self) noexcept:
        return self.best.price

    def insert_price(self, price):
        _validate_int64("price", price)
        if price <= 0:
            raise ValueError("price must be positive")
        if self._find_price_c(<int64_t>price) != NULL:
            return False
        self._insert_price_c(<int64_t>price)
        return True

    def append_order(self, price, order_id, quantity):
        _validate_int64("price", price)
        _validate_int64("order_id", order_id)
        _validate_int64("quantity", quantity)
        self._append_order_c(<int64_t>price, <int64_t>order_id, <int64_t>quantity)

    def peek_order(self, price):
        cdef int64_t order_id
        cdef int64_t quantity
        _validate_int64("price", price)
        if price <= 0:
            raise ValueError("price must be positive")
        self._peek_order_c(<int64_t>price, &order_id, &quantity)
        return order_id, quantity

    def pop_order(self, price):
        cdef int64_t order_id
        cdef int64_t quantity
        _validate_int64("price", price)
        if price <= 0:
            raise ValueError("price must be positive")
        self._pop_order_c(<int64_t>price, &order_id, &quantity)
        return order_id, quantity

    def update_front_quantity(self, price, quantity):
        _validate_int64("price", price)
        _validate_int64("quantity", quantity)
        if price <= 0:
            raise ValueError("price must be positive")
        self._update_front_quantity_c(<int64_t>price, <int64_t>quantity)

    def level_order_count(self, price):
        cdef PriceNode* level
        _validate_int64("price", price)
        if price <= 0:
            raise ValueError("price must be positive")
        level = self._find_price_c(<int64_t>price)
        return 0 if level == NULL else level.order_count

    # Compatibility methods matching the former Python BookSide API.
    def rest(self, price, order_id, quantity):
        self.append_order(price, order_id, quantity)

    def pop_best(self):
        cdef PriceNode* level = self.best
        cdef OrderNode* current
        cdef OrderNode* following
        if level == NULL:
            raise IndexError("pop from empty book side")
        current = level.head
        while current != NULL:
            following = current.next
            free(current)
            current = following
        level.head = NULL
        level.tail = NULL
        level.order_count = 0
        self._delete_node_c(level)

    def order_count(self):
        cdef list all_prices = self.prices()
        cdef object price
        cdef Py_ssize_t total = 0
        cdef PriceNode* level
        for price in all_prices:
            level = self._find_price_c(<int64_t>price)
            total += level.order_count
        return total

    def is_empty(self):
        return self.root == NULL

    def depth(self, n):
        cdef list all_prices = self.prices()
        cdef list result = []
        cdef object price
        cdef object total
        cdef PriceNode* level
        cdef OrderNode* order
        if n < 0:
            raise ValueError("depth must be non-negative")
        all_prices.sort(reverse=self.is_bid)
        for price in all_prices[:n]:
            level = self._find_price_c(<int64_t>price)
            total = 0
            order = level.head
            while order != NULL:
                total += order.quantity
                order = order.next
            result.append((price, total))
        return result

    def contains_price(self, price):
        _validate_int64("price", price)
        if price <= 0:
            raise ValueError("price must be positive")
        return self._find_price_c(<int64_t>price) != NULL

    def best_price(self):
        if self.best == NULL:
            return None
        return self.best.price

    def price_level_count(self):
        return self.level_count

    def prices(self):
        cdef list result = []
        _collect_prices(self.root, result)
        return result

    def _debug_validate(self):
        cdef Py_ssize_t actual_count = 0
        cdef int black_height
        cdef PriceNode* expected_best
        if self.root == NULL:
            if self.best != NULL or self.level_count != 0:
                raise AssertionError("Invalid empty tree state")
            return True
        if self.root.is_red:
            raise AssertionError("Root must be black")
        if self.root.parent != NULL:
            raise AssertionError("Root parent must be NULL")
        black_height = _validate_subtree(self.root, NULL, NULL, NULL, &actual_count)
        if actual_count != self.level_count:
            raise AssertionError("Tree node count mismatch")
        expected_best = self.root
        if self.is_bid:
            while expected_best.right != NULL:
                expected_best = expected_best.right
        else:
            while expected_best.left != NULL:
                expected_best = expected_best.left
        if self.best != expected_best:
            raise AssertionError("Cached best-price pointer mismatch")
        return True


cdef class CythonOrderBook:
    def __cinit__(self):
        self.bids = CythonOrderBookSide(True)
        self.asks = CythonOrderBookSide(False)

    def best_bid(self):
        return self.bids.best_price()

    def best_ask(self):
        return self.asks.best_price()

    def depth(self, n=5):
        cdef list bid_prices = self.bids.prices()
        cdef list ask_prices = self.asks.prices()
        cdef list bids = []
        cdef list asks = []
        cdef object total
        cdef PriceNode* level
        cdef OrderNode* order
        cdef object price
        if n < 0:
            raise ValueError("depth must be non-negative")
        bid_prices.sort(reverse=True)
        ask_prices.sort()
        for price in bid_prices[:n]:
            level = self.bids._find_price_c(<int64_t>price)
            total = 0
            order = level.head
            while order != NULL:
                total += order.quantity
                order = order.next
            bids.append((price, total))
        for price in ask_prices[:n]:
            level = self.asks._find_price_c(<int64_t>price)
            total = 0
            order = level.head
            while order != NULL:
                total += order.quantity
                order = order.next
            asks.append((price, total))
        return bids, asks


# Kept for backwards compatibility with existing FIFO tests.
cdef class CythonPriceLevel:
    def __cinit__(self):
        self.head = NULL
        self.tail = NULL
        self.count = 0

    def __dealloc__(self):
        cdef OrderNode* current = self.head
        cdef OrderNode* following
        while current != NULL:
            following = current.next
            free(current)
            current = following
        self.head = NULL
        self.tail = NULL
        self.count = 0

    cdef int _append_c(self, int64_t order_id, int64_t quantity) except -1:
        cdef OrderNode* node
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        node = <OrderNode*>malloc(sizeof(OrderNode))
        if node == NULL:
            raise MemoryError()
        node.order_id = order_id
        node.quantity = quantity
        node.next = NULL
        if self.tail == NULL:
            self.head = node
            self.tail = node
        else:
            self.tail.next = node
            self.tail = node
        self.count += 1
        return 0

    cdef void peek_c(self, int64_t* order_id, int64_t* quantity) except *:
        if self.head == NULL:
            raise IndexError("peek from empty price level")
        order_id[0] = self.head.order_id
        quantity[0] = self.head.quantity

    cdef void pop_front_c(self, int64_t* order_id, int64_t* quantity) except *:
        cdef OrderNode* node = self.head
        if node == NULL:
            raise IndexError("pop from empty price level")
        order_id[0] = node.order_id
        quantity[0] = node.quantity
        self.head = node.next
        if self.head == NULL:
            self.tail = NULL
        free(node)
        self.count -= 1

    cdef void update_front_quantity_c(self, int64_t quantity) except *:
        if self.head == NULL:
            raise IndexError("update on empty price level")
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        self.head.quantity = quantity

    def append(self, order_id, quantity):
        _validate_int64("order_id", order_id)
        _validate_int64("quantity", quantity)
        self._append_c(<int64_t>order_id, <int64_t>quantity)

    def is_empty(self):
        return self.head == NULL

    def order_count(self):
        return self.count

    def peek(self):
        cdef int64_t order_id
        cdef int64_t quantity
        self.peek_c(&order_id, &quantity)
        return order_id, quantity

    def pop_front(self):
        cdef int64_t order_id
        cdef int64_t quantity
        self.pop_front_c(&order_id, &quantity)
        return order_id, quantity

    def update_front_quantity(self, quantity):
        _validate_int64("quantity", quantity)
        self.update_front_quantity_c(<int64_t>quantity)
