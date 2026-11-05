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

        last_sequence = self._last_sequence

        if sequence <= last_sequence:
            raise ValueError(
                f"sequence {sequence} is not greater than last processed "
                f"{last_sequence} (duplicate or out-of-order order)"
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

        # Cache frequently accessed objects and methods locally.
        levels = opposite.levels
        best_price = opposite.best_price
        pop_best = opposite.pop_best
        rest = own.rest

        trades = []
        remaining = quantity
        best = best_price()

        next_trade_id = self._next_trade_id

        while remaining and best is not None:

            # Stop immediately if the best available price cannot match.
            if is_buy:
                if best > price:
                    break
            else:
                if best < price:
                    break

            level = levels[best]
            popleft = level.popleft

            while remaining and level:
                resting = level[0]
                resting_qty = resting[1]

                # Avoid calling Python's built-in min() for every fill.
                if remaining < resting_qty:
                    fill = remaining
                else:
                    fill = resting_qty

                if is_buy:
                    buy_id = order_id
                    sell_id = resting[0]
                else:
                    buy_id = resting[0]
                    sell_id = order_id

                trades.append((
                    next_trade_id,
                    buy_id,
                    sell_id,
                    best,
                    fill,
                    sequence,
                ))

                next_trade_id += 1
                remaining -= fill

                if fill == resting_qty:
                    popleft()
                else:
                    resting[1] = resting_qty - fill

            # Only request another best price if this level was exhausted.
            if not level:
                pop_best()

                if remaining:
                    best = best_price()
                else:
                    break
            else:
                # The level still has resting orders, so the incoming
                # order must have been completely filled.
                break

        if remaining:
            rest(price, order_id, remaining)

        self._next_trade_id = next_trade_id
        self.trades_executed += len(trades)

        return trades

    def depth(self, n=5):
        return self.book.depth(n)

    def best_bid(self):
        return self.book.best_bid()

    def best_ask(self):
        return self.book.best_ask()