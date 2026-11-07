"""
Load tests for the simulator.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest

from simulator.benchmark import run_one
from simulator.workload import MIXED


@pytest.mark.asyncio
async def test_1k_orders_no_loss():
    result = await run_one(1_000)
    assert result["accepted"] == 1_000
    assert result["missing"] == 0
    assert result["unique_ids"] == 1_000


@pytest.mark.asyncio
async def test_10k_orders_no_loss():
    result = await run_one(10_000)
    assert result["accepted"] == 10_000
    assert result["missing"] == 0
    assert result["unique_ids"] == 10_000


@pytest.mark.asyncio
async def test_reproducible_ordering():
    from simulator.market_simulator import InMemorySink, MarketSimulator, SimulatorConfig
    from simulator.workload import WorkloadConfig

    cfg = SimulatorConfig(
        workload=WorkloadConfig(kind=MIXED, count=500, seed=99),
        target_rate_per_sec=1_000_000.0,
    )
    sink_a = InMemorySink()
    sink_b = InMemorySink()
    await MarketSimulator(cfg, sink_a).run()
    await MarketSimulator(cfg, sink_b).run()

    ids_a = [o.order_id for o in sink_a.orders]
    ids_b = [o.order_id for o in sink_b.orders]
    assert ids_a == ids_b


@pytest.mark.asyncio
async def test_no_duplicates_10k():
    from simulator.market_simulator import InMemorySink, MarketSimulator, SimulatorConfig
    from simulator.workload import WorkloadConfig

    cfg = SimulatorConfig(
        workload=WorkloadConfig(kind=MIXED, count=10_000, seed=7),
        target_rate_per_sec=1_000_000.0,
    )
    sink = InMemorySink()
    await MarketSimulator(cfg, sink).run()

    ids = [o.order_id for o in sink.orders]
    assert len(ids) == len(set(ids)) == 10_000