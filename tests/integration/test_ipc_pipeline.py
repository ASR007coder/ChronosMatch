"""
End-to-end integration test: Simulator → IPC adapter → Engine stub.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest

from simulator.order_generator import Order
from simulator.producer_adapter import IPCProducerAdapter
from simulator.market_simulator import MarketSimulator, SimulatorConfig
from simulator.workload import WorkloadConfig, MIXED

class StubIPCProducer:
    def __init__(self):
        self.received: list = []
    # CHANGED: Removed 'async' because the adapter calls it synchronously
    def submit(self, order_id, sequence, price, timestamp_ns, quantity, side, timeout=None) -> bool:
        self.received.append((order_id, sequence, price, timestamp_ns, quantity, side))
        return True

class StubEngine:
    def __init__(self):
        self.processed: list = []
        self.trades: list = []
    def process(self, order_id, sequence, price, quantity, side):
        self.processed.append((order_id, sequence, price, quantity, side))
        self.trades.append((order_id, price, quantity))
        return self.trades[-1]

@pytest.mark.asyncio
async def test_simulator_to_engine_end_to_end():
    ipc = StubIPCProducer()
    engine = StubEngine()
    adapter = IPCProducerAdapter(ipc)

    class AdapterWithEngine:
        async def submit(self, order: Order) -> bool:
            ok = await adapter.submit(order)
            if ok:
                engine.process(order.order_id, order.sequence, order.price, order.quantity, order.side)
            return ok

    config = SimulatorConfig(
        workload=WorkloadConfig(kind=MIXED, count=20, seed=42),
        target_rate_per_sec=100_000.0,
    )
    sim = MarketSimulator(config, AdapterWithEngine())
    stats = await sim.run()

    assert stats.generated == 20
    assert stats.accepted == 20
    assert len(ipc.received) == 20
    assert len(engine.processed) == 20
    assert len(engine.trades) == 20
    ipc_ids = [r[0] for r in ipc.received]
    assert len(set(ipc_ids)) == 20
    assert ipc_ids == list(range(1, 21))

@pytest.mark.asyncio
async def test_end_to_end_no_silent_loss_with_rejections():
    class FlakyIPC:
        def __init__(self):
            self.received = []
            self._attempt = 0
        # CHANGED: Removed 'async' here too
        def submit(self, order_id, sequence, price, timestamp_ns, quantity, side, timeout=None):
            self._attempt += 1
            if self._attempt % 5 == 0:
                return False
            self.received.append((order_id, sequence, price, timestamp_ns, quantity, side))
            return True

    ipc = FlakyIPC()
    adapter = IPCProducerAdapter(ipc)
    config = SimulatorConfig(
        workload=WorkloadConfig(kind=MIXED, count=30, seed=1),
        target_rate_per_sec=1_000_000.0,
        max_retries_per_order=3,
    )
    sim = MarketSimulator(config, adapter)
    stats = await sim.run()
    assert stats.accepted == 30
    assert len(ipc.received) == 30