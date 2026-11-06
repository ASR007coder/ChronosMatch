# cython: language_level=3

"""Cython matching engine backed exclusively by the native Cython order book."""

from libc.stdint cimport int64_t

from backend.engine.models import BUY, Trade, validate_order
from backend.engine.cython.order_book_core cimport CythonOrderBook, CythonOrderBookSide


cdef class CythonMatchingEngine:
    cdef public CythonOrderBook book
    cdef object _next_trade_id
    cdef int64_t _last_sequence
    cdef public unsigned long long orders_processed
    cdef public unsigned long long trades_executed

    def __cinit__(self):
        self.book = CythonOrderBook()
        self._next_trade_id = 1
        self._last_sequence = 0
        self.orders_processed = 0
        self.trades_executed = 0

    def submit_order(self, order):
        return [
            Trade(*trade)
            for trade in self.submit(
                order.order_id,
                order.side,
                order.price,
                order.quantity,
                order.sequence,
            )
        ]

    def submit(self, order_id, side, price, quantity, sequence):
        cdef bint is_buy
        cdef CythonOrderBookSide opposite
        cdef CythonOrderBookSide own
        cdef int64_t best
        cdef int64_t resting_id
        cdef int64_t resting_qty
        cdef int64_t fill
        cdef int64_t remaining
        cdef object next_trade_id
        cdef list trades = []

        validate_order(side, price, quantity)

        if price > 9223372036854775807:
            raise ValueError("price must fit in signed 64-bit range")
        if quantity > 9223372036854775807:
            raise ValueError("quantity must fit in signed 64-bit range")

        if not isinstance(order_id, int) or isinstance(order_id, bool):
            raise ValueError("order_id must be an integer")
        if not isinstance(sequence, int) or isinstance(sequence, bool):
            raise ValueError("sequence must be an integer")
        if sequence < 0 or sequence > 9223372036854775807:
            raise ValueError("sequence must fit in signed 64-bit range")
        if order_id < -9223372036854775808 or order_id > 9223372036854775807:
            raise ValueError("order_id must fit in signed 64-bit range")

        if sequence <= self._last_sequence:
            raise ValueError(
                f"sequence {sequence} is not greater than last processed "
                f"{self._last_sequence} (duplicate or out-of-order order)"
            )

        is_buy = side == BUY
        if is_buy:
            opposite = self.book.asks
            own = self.book.bids
        else:
            opposite = self.book.bids
            own = self.book.asks

        remaining = <int64_t>quantity
        next_trade_id = self._next_trade_id

        # No Python dict, heap, deque, or Python price-level objects are used here.
        while remaining > 0 and opposite._has_best_c():
            best = opposite._best_price_c()

            if is_buy:
                if best > price:
                    break
            else:
                if best < price:
                    break

            opposite._peek_order_c(best, &resting_id, &resting_qty)
            fill = remaining if remaining < resting_qty else resting_qty

            if is_buy:
                trades.append((next_trade_id, order_id, resting_id, best, fill, sequence))
            else:
                trades.append((next_trade_id, resting_id, order_id, best, fill, sequence))

            next_trade_id += 1
            remaining -= fill

            if fill == resting_qty:
                # Popping the last FIFO order automatically deletes its price node.
                opposite._pop_order_c(best, &resting_id, &resting_qty)
            else:
                opposite._update_front_quantity_c(best, resting_qty - fill)

        if remaining > 0:
            own._append_order_c(<int64_t>price, <int64_t>order_id, remaining)

        self._last_sequence = <int64_t>sequence
        self.orders_processed += 1
        self._next_trade_id = next_trade_id
        self.trades_executed += len(trades)
        return trades

    def depth(self, n=5):
        return self.book.depth(n)

    def best_bid(self):
        return self.book.best_bid()

    def best_ask(self):
        return self.book.best_ask()
