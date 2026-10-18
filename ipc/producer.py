#  ipc/producer.py


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
