# ipc/consumer.py


from ipc.protocol import decode
from ipc.ring_buffer import RingBuffer


class Consumer:
    """Reads records from the ring buffer and decodes orders."""

    def __init__(self, ring_buffer: RingBuffer):
        self.ring_buffer = ring_buffer

    def receive(self, timeout=None) -> tuple[int, int, int, int, int, int]:
        """Return the decoded order fields as a tuple."""

        record = self.ring_buffer.read(timeout=timeout)
        return decode(record)

