
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DashboardSnapshot:
    best_bid: Optional[int]
    best_ask: Optional[int]
    orders_processed: int
    trades_executed: int
    latency_ns: int


def sample_snapshots():
    return [
        DashboardSnapshot(49900, 50000, 100, 20, 25000),
        DashboardSnapshot(49950, 50000, 200, 45, 30000),
        DashboardSnapshot(50000, 50100, 300, 70, 22000),
    ]
