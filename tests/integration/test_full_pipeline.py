"""
End-to-End Pipeline Test: Simulator -> Adapter -> IPC -> Engine
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest
import asyncio
import time

from simulator.runner import SimulatorRun
from simulator.market_simulator import SimulatorConfig
from simulator.workload import WorkloadConfig, MIXED


class MockIPCProducer:
    """Mocks Asif's Producer class exactly."""
    def __init__(self):
        self.buffer = [] # Acts like a ring buffer
        self.attempt_count = 0
        self.accepted_count = 0
        self.rejected_count = 0

    def submit(self, order_id, sequence, price, timestamp_ns, quantity, side, timeout=None) -> bool:
        self.attempt_count += 1
        
        # Simulate a full buffer occasionally (reject every 10th attempt)
        if self.attempt_count % 10 == 0:
            self.rejected_count += 1
            return False
        
        self.buffer.append((order_id, sequence, price, timestamp_ns, quantity, side))
        self.accepted_count += 1
        return True


class MockEngine:
    """Mocks Mahesh's Matching Engine."""
    def __init__(self):
        self.processed_orders = 0
        self.trades = 0

    def process_order(self, order_data):
        self.processed_orders += 1
        # Fake trade execution
        if self.processed_orders % 10 == 0:
            self.trades += 1


@pytest.mark.asyncio
async def test_full_pipeline_end_to_end():
    """
    Runs a real simulation through the adapter into a mock IPC, 
    then feeds the IPC buffer into a mock Engine.
    """
    # 1. Setup the pipeline
    ipc = MockIPCProducer()
    engine = MockEngine()
    
    # 2. Configure the simulator (100 orders)
    cfg = SimulatorConfig(
        workload=WorkloadConfig(kind=MIXED, count=100, seed=42),
        target_rate_per_sec=10_000.0, # Fast but yields to event loop
        max_retries_per_order=3,
    )
    
    # 3. Inject the adapter into the runner
    from simulator.producer_adapter import IPCProducerAdapter
    adapter = IPCProducerAdapter(ipc)
    
    run = SimulatorRun(cfg, sink=adapter)

    # 4. Start the simulation
    await run.start()
    await run.wait()

    # 5. Verify Simulator Stats
    stats = run.stats()
    assert stats.generated == 100
    assert stats.accepted == 100  # Should be exactly 100 due to retries
    assert stats.rejected > 0     # Should have some rejections from full buffer
    
    # 6. Verify IPC received everything (0 silent loss)
    assert len(ipc.buffer) == 100
    assert len(set([o[0] for o in ipc.buffer])) == 100 # No duplicates

    # 7. Feed the IPC buffer into the Engine
    for order_data in ipc.buffer:
        engine.process_order(order_data)

    # 8. Verify Engine processed everything
    assert engine.processed_orders == 100
    assert engine.trades == 10


@pytest.mark.asyncio
async def test_metrics_interface_for_vijay():
    """Verify the metrics dictionary is JSON-ready for Vijay's dashboard."""
    cfg = SimulatorConfig(
        workload=WorkloadConfig(kind=MIXED, count=50, seed=1),
        target_rate_per_sec=100_000.0,
    )
    run = SimulatorRun(cfg)
    await run.start()
    await run.wait()

    snapshot = run.snapshot()
    
    # Assert all keys Vijay needs are present
    required_keys = [
        "run_id", "status", "error", "generated", "submitted",
        "accepted", "rejected", "retried", "elapsed_seconds", "accepted_rate"
    ]
    for key in required_keys:
        assert key in snapshot, f"Missing metric: {key}"
        
    assert snapshot["status"] == "completed"
    assert isinstance(snapshot["accepted_rate"], float)