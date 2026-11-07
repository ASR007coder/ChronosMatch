"""
ChronosMatch — Market Simulator
Async producer loop that submits orders to a sink.

Two submission paths:
  * per-order : sinks that only implement `async submit(order) -> bool`
                (InMemorySink, RejectingSink, IPCProducerAdapter).
  * batched   : sinks that also implement `async submit_many(orders) -> int`
                (BatchIPCProducerAdapter). FIFO order is preserved and the
                return value is the number of orders accepted from the front
                of the chunk.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Protocol

from backend.simulator.order_generator import Order
from backend.simulator.workload import WorkloadConfig, build_workload


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
        if reject_every <= 0:
            raise ValueError("reject_every must be positive")
        if retry_after < 0:
            raise ValueError("retry_after must be non-negative")

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


@dataclass(slots=True)
class SimulatorConfig:
    workload: WorkloadConfig = field(default_factory=WorkloadConfig)
    target_rate_per_sec: float = 10_000.0
    max_retries_per_order: int = 3
    fail_on_rejection: bool = False
    batch_size: int = 1024  # used only by sinks that implement submit_many()

    def __post_init__(self) -> None:
        if self.target_rate_per_sec <= 0:
            raise ValueError("target_rate_per_sec must be positive")
        if self.max_retries_per_order < 0:
            raise ValueError("max_retries_per_order must be >= 0")
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")


class MarketSimulator:
    def __init__(self, config: SimulatorConfig, sink: OrderSink) -> None:
        self.config = config
        self.sink = sink
        self.stats = SimulatorStats()
        self._orders: list[Order] = build_workload(config.workload)
        self._started = False

    async def run(
        self,
        stop_event: asyncio.Event | None = None,
    ) -> SimulatorStats:
        if self._started:
            raise RuntimeError("MarketSimulator instances can only run once")

        self._started = True
        start = time.perf_counter()
        interval = 1.0 / self.config.target_rate_per_sec

        try:
            submit_many = getattr(self.sink, "submit_many", None)

            if submit_many is not None:
                await self._run_batched(
                    submit_many, start, interval, stop_event
                )
            else:
                await self._run_per_order(start, interval, stop_event)

        finally:
            self.stats.elapsed_seconds = time.perf_counter() - start

        return self.stats

    async def _pace(
        self,
        scheduled: float,
        stop_event: asyncio.Event | None,
    ) -> None:
        """Sleep until `scheduled` (perf_counter time), if it is in the future."""
        wait = scheduled - time.perf_counter()

        if wait <= 0:
            return

        if stop_event is None:
            await asyncio.sleep(wait)
        else:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=wait)
            except asyncio.TimeoutError:
                pass

    async def _run_per_order(
        self,
        start: float,
        interval: float,
        stop_event: asyncio.Event | None,
    ) -> None:
        """Original one-order-at-a-time path. Behavior unchanged."""

        for i, order in enumerate(self._orders):
            if stop_event is not None and stop_event.is_set():
                break

            self.stats.generated += 1

            await self._submit_with_retries(order, stop_event)

            if stop_event is not None and stop_event.is_set():
                break

            await self._pace(start + (i + 1) * interval, stop_event)

    async def _run_batched(
        self,
        submit_many,
        start: float,
        interval: float,
        stop_event: asyncio.Event | None,
    ) -> None:
        """
        Hand orders to the sink in contiguous chunks.

        submit_many(chunk) must return how many orders from the FRONT of
        the chunk were accepted. Any remainder goes through the per-order
        retry path, so ordering and retry semantics are preserved.
        Pacing is applied once per chunk, not once per order.
        """

        orders = self._orders
        total = len(orders)
        size = self.config.batch_size
        stats = self.stats
        i = 0

        while i < total:
            if stop_event is not None and stop_event.is_set():
                break

            chunk = orders[i:i + size]
            k = len(chunk)
            stats.generated += k

            accepted = await submit_many(chunk)
            stats.submitted += accepted
            stats.accepted += accepted

            for order in chunk[accepted:]:
                await self._submit_with_retries(order, stop_event)

            i += k

            await self._pace(start + i * interval, stop_event)

    async def _submit_with_retries(
        self,
        order: Order,
        stop_event: asyncio.Event | None = None,
    ) -> None:
        attempts = 0
        max_attempts = 1 + self.config.max_retries_per_order

        while attempts < max_attempts:
            if stop_event is not None and stop_event.is_set():
                return

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