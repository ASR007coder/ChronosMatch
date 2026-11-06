
"""Pure-Python matching engine: the correctness baseline for the Cython port.

Two entry points with identical behaviour:
  submit(order_id, side, price, quantity, sequence)
      -> list of plain tuples (hot path)
  submit_order(order)
      -> list of Trade objects (convenience/tests)

All integer inputs follow the signed 64-bit contract.
See docs/engine-interface.md for the full contract.
"""

from backend.engine.models import (
    BUY,
    INT64_MAX,
    Trade,
    validate_int64,
    validate_order,
)
from backend.engine.order_book import OrderBook


class MatchingEngine:
    def __init__(self):
        self.book = OrderBook()
        self._next_trade_id = 1
        self._last_sequence = 0
        self.orders_processed = 0
        self.trades_executed = 0

    def submit_order(self, order):
        """Submit an Order object and return Trade objects."""
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
        """Submit an order and return execution tuples.

        Execution price is the resting order's price.
        Invalid input and trade-ID exhaustion are rejected before
        modifying matching-engine state.
        """

        # Validate every integer input before touching engine state.
        validate_int64("order_id", order_id)
        validate_int64("sequence", sequence)
        validate_order(side, price, quantity)

        # Enforce strictly increasing sequence numbers.
        if sequence <= self._last_sequence:
            raise ValueError(
                f"sequence {sequence} is not greater than last processed "
                f"{self._last_sequence} (duplicate or out-of-order order)"
            )

        is_buy = side == BUY

        book = self.book
        opposite, own = (
            (book.asks, book.bids)
            if is_buy
            else (book.bids, book.asks)
        )

        trades = []
        remaining = quantity

        best = opposite.best_price()

        # Determine whether this order can match.
        while (
            remaining
            and best is not None
            and (best <= price if is_buy else best >= price)
        ):
            level = opposite.levels[best]

            while remaining and level:
                resting = level[0]
                resting_qty = resting[1]

                fill = (
                    remaining
                    if remaining < resting_qty
                    else resting_qty
                )

                if is_buy:
                    buy_id, sell_id = order_id, resting[0]
                else:
                    buy_id, sell_id = resting[0], order_id

                trades.append(
                    (
                        self._next_trade_id + len(trades),
                        buy_id,
                        sell_id,
                        best,
                        fill,
                        sequence,
                    )
                )

                remaining -= fill

                if fill == resting_qty:
                    level.popleft()
                else:
                    resting[1] = resting_qty - fill

            if not level:
                opposite.pop_best()

            best = opposite.best_price()

        # Validate trade-ID allocation before committing engine counters.
        trade_count = len(trades)

        if trade_count:
            last_trade_id = self._next_trade_id + trade_count - 1

            if last_trade_id > INT64_MAX:
                raise OverflowError(
                    "trade ID space exhausted; cannot execute this order"
                )

        # Rest any unfilled quantity.
        if remaining:
            own.rest(price, order_id, remaining)

        # Commit counters only after successful matching.
        self._next_trade_id += trade_count
        self._last_sequence = sequence
        self.orders_processed += 1
        self.trades_executed += trade_count

        return trades

    # ---- Read-only views (dashboard / tests; not on the hot path) ----

    def depth(self, n=5):
        return self.book.depth(n)

    def best_bid(self):
        return self.book.best_bid()

    def best_ask(self):
        return self.book.best_ask()
