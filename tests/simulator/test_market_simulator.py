"""
Unit tests for simulator/market_simulator.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import asyncio
import pytest

from simulator.market_simulator import (
    InMemorySink,
    MarketSimulator,
    RejectingSink,
    SimulatorConfig,
    SimulatorStats,
)
from simulator.workload import MIXED, WorkloadConfig


# ============================================================
# Basic flow
# ============================================================

@pytest.mark.asyncio
async def test_submits_all_orders_to_sink():
    cfg = SimulatorConfig(
        workload=WorkloadConfig(kind=MIXED, count=50, seed=1),
        target_rate_per_sec=10_000.0,
    )
    sink = InMemorySink()
    sim = MarketSimulator(cfg, sink)
    stats = await sim.run()

    assert stats.generated == 50
    assert stats.accepted == 50
    assert len(sink.orders) == 50


@pytest.mark.asyncio
async def test_order_ids_match():
    cfg = SimulatorConfig(
        workload=WorkloadConfig(kind=MIXED, count=20, seed=1),
        target_rate_per_sec=10_000.0,
    )
    sink = InMemorySink()
    sim = MarketSimulator(cfg, sink)
    await sim.run()

    sink_ids = [o.order_id for o in sink.orders]
    assert sink_ids == list(range(1, 21))


@pytest.mark.asyncio
async def test_zero_orders_runs_cleanly():
    cfg = SimulatorConfig(
        workload=WorkloadConfig(kind=MIXED, count=0, seed=1),
        target_rate_per_sec=10_000.0,
    )
    sink = InMemorySink()
    sim = MarketSimulator(cfg, sink)
    stats = await sim.run()

    assert stats.generated == 0
    assert stats.accepted == 0


# ============================================================
# Backpressure / retry
# ============================================================

@pytest.mark.asyncio
async def test_rejecting_sink_does_not_lose_orders():
    cfg = SimulatorConfig(
        workload=WorkloadConfig(kind=MIXED, count=50, seed=1),
        target_rate_per_sec=10_000.0,
        max_retries_per_order=5,
    )
    sink = RejectingSink(reject_every=5, retry_after=3)
    sim = MarketSimulator(cfg, sink)
    stats = await sim.run()

    # Every order should eventually be accepted (retried until success)
    assert stats.accepted == 50
    assert len(sink.orders) == 50
    assert stats.rejected > 0
    assert stats.retried > 0


@pytest.mark.asyncio
async def test_fail_on_rejection_raises():
    cfg = SimulatorConfig(
        workload=WorkloadConfig(kind=MIXED, count=20, seed=1),
        target_rate_per_sec=10_000.0,
        max_retries_per_order=0,
        fail_on_rejection=True,
    )
    sink = RejectingSink(reject_every=1)  # reject everything
    sim = MarketSimulator(cfg, sink)

    with pytest.raises(RuntimeError):
        await sim.run()


# ============================================================
# Statistics
# ============================================================

@pytest.mark.asyncio
async def test_stats_elapsed_positive():
    cfg = SimulatorConfig(
        workload=WorkloadConfig(kind=MIXED, count=10, seed=1),
        target_rate_per_sec=1_000_000.0,   # very fast
    )
    sink = InMemorySink()
    sim = MarketSimulator(cfg, sink)
    stats = await sim.run()

    assert stats.elapsed_seconds > 0
    assert stats.accepted_rate > 0


# ============================================================
# Config validation
# ============================================================

def test_negative_target_rate_rejected():
    with pytest.raises(ValueError):
        SimulatorConfig(
            workload=WorkloadConfig(count=10, seed=1),
            target_rate_per_sec=0,
        )


def test_negative_max_retries_rejected():
    with pytest.raises(ValueError):
        SimulatorConfig(
            workload=WorkloadConfig(count=10, seed=1),
            max_retries_per_order=-1,
        )


# ============================================================
# Standalone runner
# ============================================================

def _run_standalone():
    async def run_all():
        await test_submits_all_orders_to_sink()
        await test_order_ids_match()
        await test_zero_orders_runs_cleanly()
        await test_rejecting_sink_does_not_lose_orders()
        await test_fail_on_rejection_raises()
        await test_stats_elapsed_positive()
        test_negative_target_rate_rejected()
        test_negative_max_retries_rejected()
    asyncio.run(run_all())
    print("All test_market_simulator tests passed (standalone)")


if __name__ == "__main__":
    _run_standalone()
    