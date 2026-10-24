"""
ChronosMatch — Market Simulator
Seeded, reproducible order generator.
"""

import random
from dataclasses import dataclass


BUY = 0
SELL = 1


@dataclass(slots=True)
class SimulatorConfig:
    order_count: int = 10_000
    seed: int = 42
    min_price_ticks: int = 49_000
    max_price_ticks: int = 51_000
    min_quantity: int = 1
    max_quantity: int = 100
    buy_probability: float = 0.5
    target_orders_per_second: int = 10_000


@dataclass(slots=True)
class Order:
    order_id: int
    sequence: int
    price: int
    timestamp_ns: int
    quantity: int
    side: int


class OrderGenerator:
    def __init__(self, config=None):
        self.config = config or SimulatorConfig()
        self.reset()

    def reset(self):
        self._rng = random.Random(self.config.seed)
        self._next_id = 1
        self._next_sequence = 1
        self._ts = 1_700_000_000_000_000_000

    def next_order(self):
        c = self.config
        order = Order(
            order_id=self._next_id,
            sequence=self._next_sequence,
            price=self._rng.randint(c.min_price_ticks, c.max_price_ticks),
            quantity=self._rng.randint(c.min_quantity, c.max_quantity),
            side=BUY if self._rng.random() < c.buy_probability else SELL,
            timestamp_ns=self._ts,
        )
        self._next_id += 1
        self._next_sequence += 1
        self._ts += 1_000_000
        return order

    def generate(self, count):
        if count < 0:
            raise ValueError("count must be >= 0")
        return [self.next_order() for _ in range(count)]

    def __iter__(self):
        return self

    def __next__(self):
        return self.next_order()


if __name__ == "__main__":
    a = OrderGenerator(SimulatorConfig(seed=42)).generate(5)
    b = OrderGenerator(SimulatorConfig(seed=42)).generate(5)
    assert a == b
    print("order_generator.py self-test OK")
    for o in a:
        print(" ", o)