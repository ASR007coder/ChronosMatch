"""
Stress tests and edge cases for the Market Simulator.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest
import time
import asyncio

from simulator.market_simulator import (
    InMemorySink,
    MarketSimulator,
    SimulatorConfig,
)
from simulator.workload import WorkloadConfig, MIXED, BURST
from simulator.runner import SimulatorRun


@pytest.mark.asyncio
async def test_large_workload_10k():
    """Stress test: 10,000 orders without loss or duplicates."""
    cfg = SimulatorConfig(
        workload=WorkloadConfig(kind=MIXED, count=10_000, seed=42),
        target_rate_per_sec=1_000_000.0,
    )
    sink = InMemorySink()
    sim = MarketSimulator(cfg, sink)

    start = time.perf_counter()
    stats = await sim.run()
    elapsed = time.perf_counter() - start

    assert stats.accepted == 10_000
    assert len(sink.orders) == 10_000
    assert len(set(o.order_id for o in sink.orders)) == 10_000
    assert elapsed < 5.0  # Should be fast


@pytest.mark.asyncio
async def test_burst_workload_stress():
    """Stress test: Burst workload should still generate correct count."""
    cfg = SimulatorConfig(
        workload=WorkloadConfig(
            kind=BURST, count=5_000, seed=42, 
            burst_at=1000, burst_length=500, burst_multiplier=10
        ),
        target_rate_per_sec=1_000_000.0,
    )
    sink = InMemorySink()
    sim = MarketSimulator(cfg, sink)
    stats = await sim.run()

    assert stats.accepted == 5_000
    assert len(sink.orders) == 5_000


def test_invalid_config_crashes_safely():
    """Edge case: Invalid rate should raise ValueError immediately."""
    with pytest.raises(ValueError):
        SimulatorConfig(
            workload=WorkloadConfig(kind=MIXED, count=10, seed=1),
            target_rate_per_sec=-100,
        )


def test_invalid_workload_crashes_safely():
    """Edge case: Invalid workload kind should raise ValueError."""
    with pytest.raises(ValueError):
        WorkloadConfig(kind="fake_workload", count=10, seed=1)


@pytest.mark.asyncio
async def test_cancellation_cleanup():
    """Edge case: Stopping a simulator mid-run leaves stats consistent."""
    cfg = SimulatorConfig(
        workload=WorkloadConfig(kind=MIXED, count=10_000, seed=1),
        target_rate_per_sec=1_000.0, # Faster rate so the loop wakes up quicker
    )
    run = SimulatorRun(cfg)
    await run.start()
    
    # Let it run for a fraction of a second, then stop it
    await asyncio.sleep(0.1)
    await run.stop()

    # Ensure it stopped and stats are still valid
    assert run.status().value in ("stopped", "completed")
    assert run.stats().accepted <= 10_000