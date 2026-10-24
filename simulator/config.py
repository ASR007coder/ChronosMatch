"""
ChronosMatch — Market Simulator
Configuration for the simulator: order count, price/quantity bounds,
random seed, and rate target.

All price values are integer ticks (paise).
1 rupee = 100 paise.
"""

from dataclasses import dataclass


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

    def __post_init__(self):
        if self.order_count <= 0:
            raise ValueError("order_count must be positive")
        if self.min_price_ticks <= 0:
            raise ValueError("min_price_ticks must be positive")
        if self.min_price_ticks > self.max_price_ticks:
            raise ValueError("min_price_ticks > max_price_ticks")
        if self.min_quantity < 1:
            raise ValueError("min_quantity must be >= 1")
        if self.min_quantity > self.max_quantity:
            raise ValueError("min_quantity > max_quantity")
        if not 0.0 <= self.buy_probability <= 1.0:
            raise ValueError("buy_probability must be in [0, 1]")
        if self.target_orders_per_second <= 0:
            raise ValueError("target_orders_per_second must be positive")