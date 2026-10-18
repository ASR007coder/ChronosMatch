"""
End-to-end integration test: Simulator → IPC adapter → Engine stub.

Until Asif's real IPC is ready, we use a stub IPC that mimics 
the expected contract. This test proves our side works end-to-end.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest

from simulator.order_generator import Order
from simulator.producer_adapter import IPCProducerAdapter
from simulator.market_simulator import (
    MarketSimulator,
    SimulatorConfig,
)
from simulator.workload import WorkloadConfig, MIXED


# ============================================================
# Stubs for the real IPC + engine
# ============================================================

class StubIPCProducer:
    """Mimics Asif's producer. Records every order it receives."""
    def __init__(self):
        self.received: list = []

    async def submit(self, order_id, sequence, price,
                     timestamp_ns, quantity, side) -> bool:
        self.received.append(
            (order_id, sequence, price, timestamp_ns, quantity, side)
        )
        return True


class StubEngine:
    """Mimics Mahesh's matching engine. Records every order it processes."""
    def __init__(self):
        self.processed: list = []
        self.trades: list = []

    def process(self, order_id, sequence, price, quantity, side):
        self.processed.append(
            (order_id, sequence, price, quantity, side)
        )
        self.trades.append((order_id, price, quantity))
        return self.trades[-1]


# ============================================================
# Tests
# ============================================================

@pytest.mark.asyncio
async def test_simulator_to_engine_end_to_end():
    ipc = StubIPCProducer()
    engine = StubEngine()
    adapter = IPCProducerAdapter(ipc)

    class AdapterWithEngine:
        async def submit(self, order: Order) -> bool:
            ok = await adapter.submit(order)
            if ok:
                engine.process(
                    order_id=order.order_id,
                    sequence=order.sequence,
                    price=order.price,
                    quantity=order.quantity,
                    side=order.side,
                )
            return ok

    config = SimulatorConfig(
        workload=WorkloadConfig(kind=MIXED, count=20, seed=42),
        target_rate_per_sec=100_000.0,
    )

    sink = AdapterWithEngine()
    simulator = MarketSimulator(config, sink)
    stats = await simulator.run()

    assert stats.generated == 20
    assert stats.accepted == 20
    assert len(ipc.received) == 20
    assert len(engine.processed) == 20
    assert len(engine.trades) == 20

    ipc_ids = [r[0] for r in ipc.received]
    assert len(set(ipc_ids)) == 20
    assert ipc_ids == list(range(1, 21))

    engine_ids = [p[0] for p in engine.processed]
    assert engine_ids == ipc_ids


@pytest.mark.asyncio
async def test_end_to_end_no_silent_loss_with_rejections():
    class FlakyIPC:
        def __init__(self):
            self.received = []
            self._attempt = 0

        async def submit(self, order_id, sequence, price,
                         timestamp_ns, quantity, side):
            self._attempt += 1
            if self._attempt % 5 == 0:
                return False
            self.received.append(
                (order_id, sequence, price, timestamp_ns, quantity, side)
            )
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
    ids = [r[0] for r in ipc.received]
    assert len(set(ids)) == 30