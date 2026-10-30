
# cython: language_level=3

"""Cython-compiled matching engine.

Correctness-first port of the existing Python MatchingEngine.
Uses the existing Python OrderBook to preserve matching behaviour.
"""

from backend.engine.models import BUY, Trade, validate_order
from backend.engine.order_book import OrderBook


class CythonMatchingEngine:

    def __init__(self):
        self.book = OrderBook()
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
        validate_order(side, price, quantity)

        if sequence <= self._last_sequence:
            raise ValueError(
                f"sequence {sequence} is not greater than last processed "
                f"{self._last_sequence} (duplicate or out-of-order order)"
            )

        self._last_sequence = sequence
        self.orders_processed += 1

        cdef bint is_buy = side == BUY

        book = self.book

        if is_buy:
            opposite = book.asks
            own = book.bids
        else:
            opposite = book.bids
            own = book.asks

        trades = []
        remaining = quantity
        best = opposite.best_price()

        while remaining and best is not None:

            if is_buy:
                if best > price:
                    break
            else:
                if best < price:
                    break

            level = opposite.levels[best]

            while remaining and level:
                resting = level[0]
                resting_qty = resting[1]

                fill = min(remaining, resting_qty)

                if is_buy:
                    buy_id = order_id
                    sell_id = resting[0]
                else:
                    buy_id = resting[0]
                    sell_id = order_id

                trades.append((
                    self._next_trade_id,
                    buy_id,
                    sell_id,
                    best,
                    fill,
                    sequence,
                ))

                self._next_trade_id += 1
                remaining -= fill

                if fill == resting_qty:
                    level.popleft()
                else:
                    resting[1] = resting_qty - fill

            if not level:
                opposite.pop_best()

            best = opposite.best_price()

        if remaining:
            own.rest(price, order_id, remaining)

        self.trades_executed += len(trades)

        return trades

    def depth(self, n=5):
        return self.book.depth(n)

    def best_bid(self):
        return self.book.best_bid()

    def best_ask(self):
        return self.book.best_ask()
