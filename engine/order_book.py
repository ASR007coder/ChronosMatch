# backend/engine/order_book.py

"""Order book data structures. No matching logic lives here (see matching_engine.py)."""
from collections import deque
from heapq import heappop, heappush, nlargest, nsmallest


class BookSide:
    """One side of the book: price -> FIFO queue of [order_id, remaining_qty].

    A heap holds the price levels so the best price is O(1) to read. Bids store
    negated prices so the same min-heap code serves both sides. Without
    cancellation, a level only ever empties at the top, so no lazy deletion is needed.
    """
    __slots__ = ("is_bid", "levels", "_heap")

    def __init__(self, is_bid):
        self.is_bid = is_bid
        self.levels = {}
        self._heap = []

    def best_price(self):
        if not self._heap:
            return None
        key = self._heap[0]
        return -key if self.is_bid else key

    def pop_best(self):
        """Remove the (empty) best level."""
        key = heappop(self._heap)
        del self.levels[-key if self.is_bid else key]

    def rest(self, price, order_id, quantity):
        level = self.levels.get(price)
        if level is None:
            level = self.levels[price] = deque()
            heappush(self._heap, -price if self.is_bid else price)
        level.append([order_id, quantity])

    def depth(self, n):
        """Top n levels as [(price, total_qty)], best first. Not for the hot path."""
        prices = nlargest(n, self.levels) if self.is_bid else nsmallest(n, self.levels)
        return [(p, sum(o[1] for o in self.levels[p])) for p in prices]

    def order_count(self):
        return sum(len(level) for level in self.levels.values())

    def is_empty(self):
        return not self._heap


class OrderBook:
    def __init__(self):
        self.bids = BookSide(is_bid=True)
        self.asks = BookSide(is_bid=False)

    def best_bid(self):
        return self.bids.best_price()

    def best_ask(self):
        return self.asks.best_price()

    def depth(self, n=5):
        """(bids, asks), each a list of (price, total_qty), best first."""
        return self.bids.depth(n), self.asks.depth(n)
