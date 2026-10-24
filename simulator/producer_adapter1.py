"""
ChronosMatch — Market Simulator
Producer adapter: connects MarketSimulator to Asif's real IPC producer.

This is a THIN boundary. It does NOT implement IPC internals.
It only translates between our Order objects and Asif's documented
producer API.

Week 2 Day 9 work — full implementation pending Asif's API confirmation.
"""

from __future__ import annotations

from typing import Protocol

from simulator.order_generator import Order


class IPCProducerLike(Protocol):
    """
    Shape of Asif's producer as we understand it. Will be updated
    once the real API is confirmed.
    """
    async def submit(self,
                     order_id: int,
                     sequence: int,
                     price: int,
                     timestamp_ns: int,
                     quantity: int,
                     side: int) -> bool:
        ...


class IPCProducerAdapter:
    """
    Adapts our Order objects to Asif's IPC producer.

    Implements the OrderSink interface:
        async def submit(self, order: Order) -> bool

    Returns True if accepted, False if temporarily rejected.
    Raises on unexpected errors.
    """

    def __init__(self, producer: IPCProducerLike) -> None:
        self._producer = producer

    async def submit(self, order: Order) -> bool:
        # TODO (Day 9): replace with Asif's exact API call once confirmed.
        return await self._producer.submit(
            order_id=order.order_id,
            sequence=order.sequence,
            price=order.price,
            timestamp_ns=order.timestamp_ns,
            quantity=order.quantity,
            side=order.side,
        )