"""
ChronosMatch — Market Simulator
Producer adapter: connects MarketSimulator to Asif's real IPC.

This is a thin boundary. It does NOT implement IPC internals.
It only translates between our Order objects and Asif's API.
"""

from simulator.order_generator import Order


class IPCProducerAdapter:
    """
    Adapter that wraps Asif's IPC producer and exposes the
    OrderSink interface (async submit(order) -> bool).
    """

    def __init__(self, producer):
        self._producer = producer

    async def submit(self, order: Order) -> bool:
        # TODO: replace with Asif's real API call
        # Placeholder until Asif confirms the contract:
        return await self._producer.submit(
            order_id=order.order_id,
            sequence=order.sequence,
            price=order.price,
            timestamp_ns=order.timestamp_ns,
            quantity=order.quantity,
            side=order.side,
        )
