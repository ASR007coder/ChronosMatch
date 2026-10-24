"""
Unit tests for rate control in market_simulator.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import time
import pytest
from simulator.market_simulator import (
    InMemorySink, MarketSimulator, RejectingSink, SimulatorConfig,
)
from simulator.workload import WorkloadConfig


@pytest.mark.asyncio
async def test_zero_target_rate_rejected():
    with pytest.raises(ValueError):
        SimulatorConfig(
            workload=WorkloadConfig(count=10, seed=1),
            target_rate_per_sec=0,
        )


@pytest.mark.asyncio
async def test_negative_target_rate_rejected():
    with pytest.raises(ValueError):
        SimulatorConfig(
            workload=WorkloadConfig(count=10, seed=1),
            target_rate_per_sec=-100,
        )


@pytest.mark.asyncio
async def test_high_rate_completes_quickly():
    cfg = SimulatorConfig(
        workload=WorkloadConfig(count=1000, seed=1),
        target_rate_per_sec=100_000.0,
    )
    sink = InMemorySink()
    start = time.perf_counter()
    stats = await MarketSimulator(cfg, sink).run()
    elapsed = time.perf_counter() - start
    assert stats.accepted == 1000
    assert elapsed < 2.0


@pytest.mark.asyncio
async def test_finite_run_stops_at_requested_count():
    cfg = SimulatorConfig(
        workload=WorkloadConfig(count=500, seed=42),
        target_rate_per_sec=1_000_000.0,
    )
    sink = InMemorySink()
    stats = await MarketSimulator(cfg, sink).run()
    assert stats.generated == 500
    assert stats.accepted == 500
    assert len(sink.orders) == 500


@pytest.mark.asyncio
async def test_accepted_rate_is_computed():
    cfg = SimulatorConfig(
        workload=WorkloadConfig(count=100, seed=1),
        target_rate_per_sec=100_000.0,
    )
    sink = InMemorySink()
    stats = await MarketSimulator(cfg, sink).run()
    assert stats.elapsed_seconds > 0
    assert stats.accepted_rate > 0


@pytest.mark.asyncio
async def test_rejected_orders_not_counted_as_accepted():
    cfg = SimulatorConfig(
        workload=WorkloadConfig(count=50, seed=1),
        target_rate_per_sec=100_000.0,
        max_retries_per_order=5,
    )
    sink = RejectingSink(reject_every=10, retry_after=2)
    stats = await MarketSimulator(cfg, sink).run()
    assert stats.accepted == 50
    assert stats.rejected > 0
    assert stats.retried > 0


@pytest.mark.asyncio
async def test_no_silent_loss_with_backpressure():
    cfg = SimulatorConfig(
        workload=WorkloadConfig(count=100, seed=42),
        target_rate_per_sec=100_000.0,
        max_retries_per_order=5,
    )
    sink = RejectingSink(reject_every=7, retry_after=3)
    await MarketSimulator(cfg, sink).run()
    assert len(sink.orders) == 100
    assert len(set(o.order_id for o in sink.orders)) == 100