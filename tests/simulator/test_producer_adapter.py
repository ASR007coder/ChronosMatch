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
    def __init__(self):
        self.received = []
    # MUST accept timeout=None so the adapter doesn't crash
    def submit(self, order_id, sequence, price, timestamp_ns, quantity, side, timeout=None):
        self.received.append((order_id, sequence, price, timestamp_ns, quantity, side))
        return True

class RejectingProducer:
    def submit(self, *args, **kwargs):
        return False

class TimeoutProducer:
    def submit(self, *args, **kwargs):
        raise TimeoutError("buffer full")

class CrashProducer:
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

@pytest.mark.asyncio
async def test_adapter_returns_rejection_as_false():
    adapter = IPCProducerAdapter(RejectingProducer())
    gen = OrderGenerator(SimulatorConfig(order_count=1, seed=1))
    ok = await adapter.submit(gen.next_order())
    assert ok is False

@pytest.mark.asyncio
async def test_adapter_raises_producer_full_on_timeout():
    adapter = IPCProducerAdapter(TimeoutProducer())
    gen = OrderGenerator(SimulatorConfig(order_count=1, seed=1))
    with pytest.raises(ProducerFull):
        await adapter.submit(gen.next_order())

@pytest.mark.asyncio
async def test_adapter_raises_producer_error_on_crash():
    adapter = IPCProducerAdapter(CrashProducer())
    gen = OrderGenerator(SimulatorConfig(order_count=1, seed=1))
    with pytest.raises(ProducerError):
        await adapter.submit(gen.next_order())