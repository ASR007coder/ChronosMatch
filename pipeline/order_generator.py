"""
ChronosMatch — Member 2: Order Pipeline
Seeded, reproducible fake market-order generator.

Sequence starts at 1 and increments by 1 for every order.
Price is an integer in paise (10100 = Rs 101.00).
Side is BUY or SELL imported from engine.models.

The generator is deterministic: constructing it with the same
seed always produces the same sequence of orders. This is
required for reproducible tests.
"""

import random
from dataclasses import dataclass
from typing import Iterator, Optional

from pipeline.order_format import BUY, SELL


# Defaults — tune in one place.
DEFAULT_PRICE_MIN_PAISE = 9900       # Rs 99.00
DEFAULT_PRICE_MAX_PAISE = 10100      # Rs 101.00
DEFAULT_QTY_MIN = 1
DEFAULT_QTY_MAX = 100


@dataclass(slots=True)
class GeneratedOrder:
    """A single generated order, before binary encoding."""
    order_id: int
    sequence: int
    price: int
    timestamp_ns: int
    quantity: int
    side: int


class OrderGenerator:
    """
    Deterministic, seeded order generator.

    Usage:
        g = OrderGenerator(seed=42)
        first = next(g)
        second = next(g)
        # rerun:
        g2 = OrderGenerator(seed=42)
        assert next(g2) == first
    """

    def __init__(
        self,
        seed: int = 0,
        price_min_paise: int = DEFAULT_PRICE_MIN_PAISE,
        price_max_paise: int = DEFAULT_PRICE_MAX_PAISE,
        qty_min: int = DEFAULT_QTY_MIN,
        qty_max: int = DEFAULT_QTY_MAX,
        timestamp_start_ns: int = 1_700_000_000_000_000_000,
        timestamp_step_ns: int = 1_000_000,     # 1 ms between orders
    ) -> None:
        if price_min_paise > price_max_paise:
            raise ValueError("price_min_paise must be <= price_max_paise")
        if qty_min < 1 or qty_max < qty_min:
            raise ValueError("qty_min/qty_max invalid")

        self._rng = random.Random(seed)
        self._price_min = price_min_paise
        self._price_max = price_max_paise
        self._qty_min = qty_min
        self._qty_max = qty_max
        self._ts = timestamp_start_ns
        self._ts_step = timestamp_step_ns

        self._next_sequence = 1          # sequence starts at 1
        self._next_order_id = 1

    # --- single order ------------------------------------------------

    def next_order(self) -> GeneratedOrder:
        """Return the next generated order."""
        side = self._rng.choice((BUY, SELL))
        price = self._rng.randint(self._price_min, self._price_max)
        quantity = self._rng.randint(self._qty_min, self._qty_max)

        order = GeneratedOrder(
            order_id=self._next_order_id,
            sequence=self._next_sequence,
            price=price,
            timestamp_ns=self._ts,
            quantity=quantity,
            side=side,
        )

        self._next_order_id += 1
        self._next_sequence += 1
        self._ts += self._ts_step
        return order

    # --- iterator protocol -------------------------------------------

    def __iter__(self) -> Iterator[GeneratedOrder]:
        return self

    def __next__(self) -> GeneratedOrder:
        return self.next_order()

    # --- bounded iterator --------------------------------------------

    def take(self, n: int) -> list:
        """Return the next `n` orders as a list."""
        return [self.next_order() for _ in range(n)]


# --- Module-level convenience ----------------------------------------

def generate_orders(seed: int, count: int, **kwargs) -> list:
    """One-shot helper: return `count` orders from a fresh generator."""
    g = OrderGenerator(seed=seed, **kwargs)
    return g.take(count)


# --- Self-test -------------------------------------------------------

if __name__ == "__main__":
    # Same seed must produce identical orders.
    a = generate_orders(seed=1234, count=5)
    b = generate_orders(seed=1234, count=5)
    assert a == b, "same seed must yield same orders"

    # Different seed should differ (with high probability).
    c = generate_orders(seed=9999, count=5)
    assert a != c, "different seed should differ"

    # Sequence must start at 1 and increment by 1.
    seqs = [o.sequence for o in a]
    assert seqs == [1, 2, 3, 4, 5], f"bad sequence: {seqs}"

    # Prices must be integers in range, sides must be valid.
    for o in a:
        assert isinstance(o.price, int)
        assert DEFAULT_PRICE_MIN_PAISE <= o.price <= DEFAULT_PRICE_MAX_PAISE
        assert o.side in (BUY, SELL)

    print("order_generator.py self-test OK")
    print("First 5 orders:")
    for o in a:
        print(" ", o)
