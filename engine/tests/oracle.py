"""Deliberately naive, obviously-correct engine used to cross-check the real ones."""
from engine.models import BUY


class NaiveEngine:
    def __init__(self):
        self.bids, self.asks = [], []   # entries: [arrival, order_id, price, qty]
        self.arrival = 0
        self.trade_id = 1

    def submit(self, order_id, side, price, quantity, sequence):
        trades, rem = [], quantity
        book = self.asks if side == BUY else self.bids
        while rem:
            if side == BUY:
                cands = [o for o in book if o[2] <= price]
                key = lambda o: (o[2], o[0])
            else:
                cands = [o for o in book if o[2] >= price]
                key = lambda o: (-o[2], o[0])
            if not cands:
                break
            best = min(cands, key=key)
            fill = min(rem, best[3])
            b, s = (order_id, best[1]) if side == BUY else (best[1], order_id)
            trades.append((self.trade_id, b, s, best[2], fill, sequence))
            self.trade_id += 1
            rem -= fill
            best[3] -= fill
            if best[3] == 0:
                book.remove(best)
        if rem:
            self.arrival += 1
            (self.bids if side == BUY else self.asks).append(
                [self.arrival, order_id, price, rem])
        return trades

    def depth(self, n=5):
        def agg(book, reverse):
            levels = {}
            for o in book:
                levels[o[2]] = levels.get(o[2], 0) + o[3]
            return sorted(levels.items(), reverse=reverse)[:n]
        return agg(self.bids, True), agg(self.asks, False)
