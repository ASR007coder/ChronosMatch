
"""Shared data models for the matching engine.

Pipeline and monitoring modules import BUY, SELL, Order, and Trade from here.
All integer fields use signed 64-bit bounds to match the Cython implementation.
"""

from dataclasses import dataclass
from typing import NamedTuple


BUY = 0
SELL = 1

SIDE_NAMES = {
    BUY: "BUY",
    SELL: "SELL",
}

INT64_MIN = -(2**63)
INT64_MAX = (2**63) - 1


def validate_int64(name: str, value: int) -> None:
    """Validate that a value is an integer within signed 64-bit range."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{name} must be an int, got {value!r}")

    if value < INT64_MIN or value > INT64_MAX:
        raise ValueError(
            f"{name} must fit in signed 64-bit range, got {value!r}"
        )


def validate_order(side: int, price: int, quantity: int) -> None:
    """Validate side, price, and quantity for both Order() and submit()."""
    validate_int64("side", side)
    validate_int64("price", price)
    validate_int64("quantity", quantity)

    if side != BUY and side != SELL:
        raise ValueError(
            f"invalid side {side!r}; expected BUY={BUY} or SELL={SELL}"
        )

    if price <= 0:
        raise ValueError(
            f"price must be a positive integer, got {price!r}"
        )

    if quantity <= 0:
        raise ValueError(
            f"quantity must be a positive integer, got {quantity!r}"
        )


@dataclass(frozen=True)
class Order:
    """Immutable order submitted to the matching engine."""

    order_id: int
    sequence: int
    side: int
    price: int          # Integer ticks (paise). Never float.
    quantity: int
    timestamp_ns: int = 0  # Informational only.

    def __post_init__(self) -> None:
        for name in (
            "order_id",
            "sequence",
            "side",
            "price",
            "quantity",
            "timestamp_ns",
        ):
            validate_int64(name, getattr(self, name))

        validate_order(self.side, self.price, self.quantity)


class Trade(NamedTuple):
    """A completed execution between a buy and sell order."""

    trade_id: int
    buy_order_id: int
    sell_order_id: int
    price: int
    quantity: int
    sequence: int
