"""
Unit tests for simulator/producer_adapter.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest

from simulator.order_generator import OrderGenerator, SimulatorConfig
from simulator.producer_adapter import (
    IPCProducerAdapter,
    ProducerError,
    ProducerFull,
)


class StubProducer:
    """Records calls, always accepts."""
    def __init__(self):
        self.received = []

    def submit(self, order_id, sequence, price, timestamp_ns, quantity, side, timeout=None):
        self.received.append(
            (order_id, sequence, price, timestamp_ns, quantity, side)
        )
        return True


class RejectingProducer:
    """Returns False."""
    def submit(self, *args, **kwargs):
        return False


class TimeoutProducer:
    """Raises TimeoutError to simulate a full buffer."""
    def submit(self, *args, **kwargs):
        raise TimeoutError("buffer full")


class CrashProducer:
    """Raises RuntimeError to simulate an IPC crash."""
    def submit(self, *args, **kwargs):
        raise RuntimeError("IPC crashed")


@pytest.mark.asyncio
async def test_adapter_forwards_order_fields():
    producer = StubProducer()
    adapter = IPCProducerAdapter(producer)
    gen = OrderGenerator(SimulatorConfig(order_count=5, seed=42))

    for order in gen.generate(5):
        ok = await adapter.submit(order)
        assert ok is True

    assert len(producer.received) == 5
    assert producer.received[0][0] == 1


@pytest.mark.asyncio
async def test_adapter_returns_rejection_as_false():
    adapter = IPCProducerAdapter(RejectingProducer())
    gen = OrderGenerator(SimulatorConfig(order_count=1, seed=1))
    order = gen.next_order()

    ok = await adapter.submit(order)
    assert ok is False


@pytest.mark.asyncio
async def test_adapter_preserves_all_fields():
    producer = StubProducer()
    adapter = IPCProducerAdapter(producer)
    gen = OrderGenerator(SimulatorConfig(order_count=1, seed=7))
    order = gen.next_order()

    await adapter.submit(order)
    received = producer.received[0]
    assert received[0] == order.order_id
    assert received[1] == order.sequence
    assert received[2] == order.price
    assert received[3] == order.timestamp_ns
    assert received[4] == order.quantity
    assert received[5] == order.side


@pytest.mark.asyncio
async def test_adapter_raises_producer_full_on_timeout():
    adapter = IPCProducerAdapter(TimeoutProducer())
    gen = OrderGenerator(SimulatorConfig(order_count=1, seed=1))
    order = gen.next_order()

    with pytest.raises(ProducerFull):
        await adapter.submit(order)


@pytest.mark.asyncio
async def test_adapter_raises_producer_error_on_crash():
    adapter = IPCProducerAdapter(CrashProducer())
    gen = OrderGenerator(SimulatorConfig(order_count=1, seed=1))
    order = gen.next_order()

    with pytest.raises(ProducerError):
        await adapter.submit(order)