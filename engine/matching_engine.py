"""Pure-Python matching engine: the correctness baseline for the Cython port.

Two entry points with identical behaviour:
  submit(order_id, side, price, quantity, sequence) -> list of plain tuples (hot path)
  submit_order(order) -> list of Trade, for convenience/tests
See docs/engine-interface.md for the full contract.
"""
from engine.models import BUY, Trade, validate_order
from engine.order_book import OrderBook


class MatchingEngine:
    def __init__(self):
        self.book = OrderBook()
        self._next_trade_id = 1
        self._last_sequence = 0
        self.orders_processed = 0
        self.trades_executed = 0

    def submit_order(self, order):
        return [Trade(*t) for t in self.submit(
            order.order_id, order.side, order.price, order.quantity, order.sequence)]

    def submit(self, order_id, side, price, quantity, sequence):
        validate_order(side, price, quantity)
        if sequence <= self._last_sequence:
            raise ValueError(
                f"sequence {sequence} is not greater than last processed "
                f"{self._last_sequence} (duplicate or out-of-order order)")
        self._last_sequence = sequence
        self.orders_processed += 1

        is_buy = side == BUY
        book = self.book
        opposite, own = (book.asks, book.bids) if is_buy else (book.bids, book.asks)
        trades = []
        remaining = quantity

        best = opposite.best_price()
        while remaining and best is not None and (best <= price if is_buy else best >= price):
            level = opposite.levels[best]
            while remaining and level:
                resting = level[0]
                resting_qty = resting[1]
                fill = remaining if remaining < resting_qty else resting_qty
                if is_buy:
                    buy_id, sell_id = order_id, resting[0]
                else:
                    buy_id, sell_id = resting[0], order_id
                # Execution price is the RESTING order's price.
                trades.append((self._next_trade_id, buy_id, sell_id, best, fill, sequence))
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

    # ---- read-only views (dashboard / tests; not on the hot path) ----
    def depth(self, n=5):
        return self.book.depth(n)

    def best_bid(self):
        return self.book.best_bid()

    def best_ask(self):
        return self.book.best_ask()
