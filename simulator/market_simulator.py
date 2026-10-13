"""
ChronosMatch — Market Simulator
Async producer loop that submits orders to a sink.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Protocol

from simulator.order_generator import Order
from simulator.workload import WorkloadConfig, build_workload


# ============================================================
# Sink interface
# ============================================================

class OrderSink(Protocol):
    async def submit(self, order: Order) -> bool:
        ...


class InMemorySink:
    def __init__(self) -> None:
        self.orders: list[Order] = []
        self.accepted = 0
        self.rejected = 0

    async def submit(self, order: Order) -> bool:
        self.orders.append(order)
        self.accepted += 1
        return True


class RejectingSink:
    def __init__(self, reject_every: int = 5, retry_after: int = 3) -> None:
        self.orders: list[Order] = []
        self.accepted = 0
        self.rejected = 0
        self.reject_every = reject_every
        self.retry_after = retry_after
        self._attempt = 0
        self._rejections_left = 0

    async def submit(self, order: Order) -> bool:
        self._attempt += 1
        if self._rejections_left > 0:
            self._rejections_left -= 1
            self.rejected += 1
            return False
        if self._attempt % self.reject_every == 0:
            self._rejections_left = self.retry_after
            self.rejected += 1
            return False
        self.orders.append(order)
        self.accepted += 1
        return True


# ============================================================
# Statistics
# ============================================================

@dataclass(slots=True)
class SimulatorStats:
    generated: int = 0
    submitted: int = 0
    accepted: int = 0
    rejected: int = 0
    retried: int = 0
    elapsed_seconds: float = 0.0

    @property
    def accepted_rate(self) -> float:
        if self.elapsed_seconds <= 0:
            return 0.0
        return self.accepted / self.elapsed_seconds

    def summary(self) -> str:
        return (
            f"generated={self.generated}  submitted={self.submitted}  "
            f"accepted={self.accepted}  rejected={self.rejected}  "
            f"retried={self.retried}  elapsed={self.elapsed_seconds:.3f}s  "
            f"accepted_rate={self.accepted_rate:,.0f}/s"
        )


# ============================================================
# Simulator
# ============================================================

@dataclass(slots=True)
class SimulatorConfig:
    workload: WorkloadConfig = field(default_factory=WorkloadConfig)
    target_rate_per_sec: float = 10_000.0
    max_retries_per_order: int = 3
    fail_on_rejection: bool = False

    def __post_init__(self):
        if self.target_rate_per_sec <= 0:
            raise ValueError("target_rate_per_sec must be positive")
        if self.max_retries_per_order < 0:
            raise ValueError("max_retries_per_order must be >= 0")


class MarketSimulator:
    def __init__(self, config: SimulatorConfig, sink: OrderSink) -> None:
        if config.target_rate_per_sec <= 0:
            raise ValueError("target_rate_per_sec must be positive")
        if config.max_retries_per_order < 0:
            raise ValueError("max_retries_per_order must be >= 0")

        self.config = config
        self.sink = sink
        self.stats = SimulatorStats()
        self._orders: list[Order] = build_workload(config.workload)

    async def run(self) -> SimulatorStats:
        start = time.perf_counter()
        interval = 1.0 / self.config.target_rate_per_sec

        try:
            for order in self._orders:
                self.stats.generated += 1
                await self._submit_with_retries(order)
                if interval > 0:
                    await asyncio.sleep(interval)
        finally:
            self.stats.elapsed_seconds = time.perf_counter() - start

        return self.stats

    async def _submit_with_retries(self, order: Order) -> None:
        attempts = 0
        max_attempts = 1 + self.config.max_retries_per_order

        while attempts < max_attempts:
            self.stats.submitted += 1
            accepted = await self.sink.submit(order)
            if accepted:
                self.stats.accepted += 1
                return
            attempts += 1
            self.stats.rejected += 1
            if attempts < max_attempts:
                self.stats.retried += 1
                await asyncio.sleep(0)

        if self.config.fail_on_rejection:
            raise RuntimeError(
                f"order {order.order_id} rejected {max_attempts} times"
            )


# ============================================================
# Demo
# ============================================================

async def _demo() -> None:
    cfg = SimulatorConfig(
        workload=WorkloadConfig(count=100, seed=42),
        target_rate_per_sec=1_000.0,
    )
    sink = InMemorySink()
    sim = MarketSimulator(cfg, sink)
    stats = await sim.run()

    print("MarketSimulator demo")
    print(f"  {stats.summary()}")
    print(f"  orders in sink: {len(sink.orders)}")
    assert stats.accepted == 100
    assert len(sink.orders) == 100
    print("  self-test OK")


if __name__ == "__main__":
    asyncio.run(_demo())