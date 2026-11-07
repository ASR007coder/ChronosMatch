"""
Unit tests for simulator/market_simulator.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest
from simulator.market_simulator import (
    InMemorySink, MarketSimulator, RejectingSink, SimulatorConfig,
)
from simulator.workload import MIXED, WorkloadConfig


@pytest.mark.asyncio
async def test_submits_all_orders_to_sink():
    cfg = SimulatorConfig(
        workload=WorkloadConfig(kind=MIXED, count=50, seed=1),
        target_rate_per_sec=10_000.0,
    )
    sink = InMemorySink()
    stats = await MarketSimulator(cfg, sink).run()
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
    await MarketSimulator(cfg, sink).run()
    sink_ids = [o.order_id for o in sink.orders]
    assert sink_ids == list(range(1, 21))


@pytest.mark.asyncio
async def test_zero_orders_runs_cleanly():
    cfg = SimulatorConfig(
        workload=WorkloadConfig(kind=MIXED, count=0, seed=1),
        target_rate_per_sec=10_000.0,
    )
    sink = InMemorySink()
    stats = await MarketSimulator(cfg, sink).run()
    assert stats.generated == 0
    assert stats.accepted == 0


@pytest.mark.asyncio
async def test_rejecting_sink_does_not_lose_orders():
    cfg = SimulatorConfig(
        workload=WorkloadConfig(kind=MIXED, count=50, seed=1),
        target_rate_per_sec=10_000.0,
        max_retries_per_order=5,
    )
    sink = RejectingSink(reject_every=5, retry_after=3)
    stats = await MarketSimulator(cfg, sink).run()
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
    sink = RejectingSink(reject_every=1)
    with pytest.raises(RuntimeError):
        await MarketSimulator(cfg, sink).run()


@pytest.mark.asyncio
async def test_stats_elapsed_positive():
    cfg = SimulatorConfig(
        workload=WorkloadConfig(kind=MIXED, count=10, seed=1),
        target_rate_per_sec=1_000_000.0,
    )
    sink = InMemorySink()
    stats = await MarketSimulator(cfg, sink).run()
    assert stats.elapsed_seconds > 0
    assert stats.accepted_rate > 0


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