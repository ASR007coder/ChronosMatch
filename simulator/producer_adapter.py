"""
ChronosMatch — Market Simulator
Producer adapter: connects MarketSimulator to Asif's real IPC producer.
"""

from __future__ import annotations
from typing import Protocol, Optional
from simulator.order_generator import Order


class ProducerError(Exception):
    """Base for any producer-level failure."""

class ProducerRejected(ProducerError):
    """The producer explicitly rejected this order."""

class ProducerFull(ProducerError):
    """The producer's buffer was full (timeout)."""


class IPCProducerLike(Protocol):
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
    def __init__(self, producer: IPCProducerLike, timeout: float = 1.0) -> None:
        self._producer = producer
        self._timeout = timeout

    async def submit(self, order: Order) -> bool:
        try:
            return self._producer.submit(
                order_id=order.order_id,
                sequence=order.sequence,
                price=order.price,
                timestamp_ns=order.timestamp_ns,
                quantity=order.quantity,
                side=order.side,
                timeout=self._timeout,
            )
        except TimeoutError as e:
            raise ProducerFull(str(e)) from e
        except Exception as e:
            raise ProducerError(f"unexpected producer error: {e}") from e