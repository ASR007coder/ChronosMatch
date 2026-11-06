from libc.stdint cimport int64_t

cdef struct OrderNode:
    int64_t order_id
    int64_t quantity
    OrderNode* next

cdef struct PriceNode:
    int64_t price
    PriceNode* left
    PriceNode* right
    PriceNode* parent
    bint is_red
    OrderNode* head
    OrderNode* tail
    Py_ssize_t order_count

cdef class CythonOrderBookSide:
    cdef PriceNode* root
    cdef PriceNode* best
    cdef Py_ssize_t level_count
    cdef bint is_bid

    cdef PriceNode* _find_price_c(self, int64_t price) noexcept
    cdef PriceNode* _insert_price_c(self, int64_t price) except NULL
    cdef void _left_rotate(self, PriceNode* node) noexcept
    cdef void _right_rotate(self, PriceNode* node) noexcept
    cdef void _insert_fixup(self, PriceNode* node) noexcept
    cdef void _free_tree(self, PriceNode* node) noexcept
    cdef void _transplant_c(self, PriceNode* old_node, PriceNode* new_node) noexcept
    cdef void _delete_fixup_c(self, PriceNode* node, PriceNode* parent) noexcept
    cdef void _delete_node_c(self, PriceNode* node) noexcept
    cdef void _recompute_best_c(self) noexcept
    cdef int _append_order_c(self, int64_t price, int64_t order_id, int64_t quantity) except -1
    cdef void _peek_order_c(self, int64_t price, int64_t* order_id, int64_t* quantity) except *
    cdef void _pop_order_c(self, int64_t price, int64_t* order_id, int64_t* quantity) except *
    cdef void _update_front_quantity_c(self, int64_t price, int64_t quantity) except *
    cdef bint _has_best_c(self) noexcept
    cdef int64_t _best_price_c(self) noexcept

cdef class CythonOrderBook:
    cdef public CythonOrderBookSide bids
    cdef public CythonOrderBookSide asks

cdef class CythonPriceLevel:
    cdef OrderNode* head
    cdef OrderNode* tail
    cdef Py_ssize_t count
    cdef int _append_c(self, int64_t order_id, int64_t quantity) except -1
    cdef void peek_c(self, int64_t* order_id, int64_t* quantity) except *
    cdef void pop_front_c(self, int64_t* order_id, int64_t* quantity) except *
    cdef void update_front_quantity_c(self, int64_t quantity) except *
