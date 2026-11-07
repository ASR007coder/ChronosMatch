
# backend/ipc/producer.py

from typing import Iterable

from backend.ipc.protocol import encode
from backend.ipc.ring_buffer import RingBuffer


class Producer:
    """Validates, encodes, and submits orders to the ring buffer."""

    def __init__(self, ring_buffer: RingBuffer):
        self.ring_buffer = ring_buffer

    def submit(
        self,
        order_id: int,
        sequence: int,
        price: int,
        timestamp_ns: int,
        quantity: int,
        side: int,
        timeout=None,
    ) -> bool:
        """Return True only after the record is published successfully."""

        record = encode(
            order_id=order_id,
            sequence=sequence,
            price=price,
            timestamp_ns=timestamp_ns,
            quantity=quantity,
            side=side,
        )

        self.ring_buffer.write(record, timeout=timeout)
        return True

    def submit_many(
        self,
        orders: Iterable[tuple[int, int, int, int, int, int]],
        timeout=None,
    ) -> int:
        """
        Encode and publish a batch of orders.

        Each order must be:
            (order_id, sequence, price, timestamp_ns, quantity, side)

        Returns the number of published orders.
        """

        records = [
            encode(
                order_id=order_id,
                sequence=sequence,
                price=price,
                timestamp_ns=timestamp_ns,
                quantity=quantity,
                side=side,
            )
            for order_id, sequence, price, timestamp_ns, quantity, side in orders
        ]

        return self.ring_buffer.write_many(records, timeout=timeout)
