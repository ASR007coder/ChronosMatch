"""
ChronosMatch — Market Simulator
Producer adapter: connects MarketSimulator to Asif's real IPC producer.

Wired to Asif's Producer.submit() signature:
    def submit(order_id, sequence, price, timestamp_ns, quantity, side, timeout=None) -> bool
"""

from __future__ import annotations
from typing import Protocol, Optional
from simulator.order_generator import Order


class IPCProducerLike(Protocol):
    # Note: Not async, because Asif's code is synchronous
    def submit(self,
               order_id: int,
               sequence: int,
               price: int,
               timestamp_ns: int,
               quantity: int,
               side: int,
               timeout: Optional[float] = None) -> bool:
        ...


class IPCProducerAdapter:
    """
    Adapts our Order objects to Asif's IPC producer.
    Implements the async OrderSink interface for our simulator.
    """

    def __init__(self, producer: IPCProducerLike, timeout: float = 1.0) -> None:
        self._producer = producer
        self._timeout = timeout

    async def submit(self, order: Order) -> bool:
        # Call Asif's synchronous function directly
        return self._producer.submit(
            order_id=order.order_id,
            sequence=order.sequence,
            price=order.price,
            timestamp_ns=order.timestamp_ns,
            quantity=order.quantity,
            side=order.side,
            timeout=self._timeout,
        )