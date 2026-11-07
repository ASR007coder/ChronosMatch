
from backend.ipc.protocol import decode
from backend.ipc.ring_buffer import RingBuffer


class Consumer:
    """Reads records from the ring buffer and decodes orders."""

    def __init__(self, ring_buffer: RingBuffer):
        self.ring_buffer = ring_buffer

    def receive(self, timeout=None) -> tuple[int, int, int, int, int, int]:
        """Return one decoded order."""

        record = self.ring_buffer.read(timeout=timeout)
        return decode(record)

    def receive_many(
        self,
        max_records=32,
        timeout=None,
    ) -> list[tuple[int, int, int, int, int, int]]:
        """Return up to max_records decoded orders in FIFO order."""

        records = self.ring_buffer.read_many(
            max_records=max_records,
            timeout=timeout,
        )

        return [decode(record) for record in records]
