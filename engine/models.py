# backend/engine/models


"""Shared data model. pipeline/ and monitoring/ import BUY/SELL/Order/Trade from here."""
from dataclasses import dataclass
from typing import NamedTuple

BUY = 0
SELL = 1
SIDE_NAMES = {BUY: "BUY", SELL: "SELL"}


def validate_order(side, price, quantity):
    """Validate side, price, and quantity for both Order() and submit()."""
    if not isinstance(side, int) or isinstance(side, bool):
        raise ValueError(f"side must be an int, got {side!r}")

    if side != BUY and side != SELL:
        raise ValueError(f"invalid side {side!r}; expected BUY={BUY} or SELL={SELL}")

    if not isinstance(price, int) or isinstance(price, bool):
        raise ValueError(f"price must be an int, got {price!r}")

    if price <= 0:
        raise ValueError(f"price must be a positive integer, got {price!r}")

    if not isinstance(quantity, int) or isinstance(quantity, bool):
        raise ValueError(f"quantity must be an int, got {quantity!r}")

    if quantity <= 0:
        raise ValueError(f"quantity must be a positive integer, got {quantity!r}")
@dataclass(frozen=True)
class Order:
    order_id: int
    sequence: int
    side: int
    price: int          # integer ticks (paise). Never float.
    quantity: int
    timestamp_ns: int = 0   # informational only
    def __post_init__(self):
        for name in ("order_id", "sequence", "side", "price", "quantity"):
            if not isinstance(getattr(self, name), int) or isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be an int, got {getattr(self, name)!r}")
        validate_order(self.side, self.price, self.quantity)


class Trade(NamedTuple):
    trade_id: int
    buy_order_id: int
    sell_order_id: int
    price: int          
    quantity: int
    sequence: int       
