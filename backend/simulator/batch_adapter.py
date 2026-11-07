import asyncio
import struct
import time
from operator import attrgetter

from backend.ipc.fast_ring import FastRing, RingTimeout
from backend.ipc.protocol import ORDER_RECORD_SIZE, ORDER_STRUCT, encode
from backend.simulator.producer_adapter import ProducerError, ProducerFull

_FIELDS = attrgetter(
    "order_id", "sequence", "price", "timestamp_ns", "quantity", "side"
)


def encode_orders(orders) -> bytes:
    """
    Encode Order objects into one contiguous N*64-byte buffer, in order.
    Any invalid order falls back to protocol.encode(), which raises
    the exact original exception.
    """
    buf = bytearray(len(orders) * ORDER_RECORD_SIZE)
    pack_into = ORDER_STRUCT.pack_into
    off = 0
    try:
        for row in map(_FIELDS, orders):
            order_id, sequence, price, ts, quantity, side = row
            if sequence < 1 or price < 1 or quantity < 1 or side < 0 or side > 1:
                raise ValueError
            pack_into(buf, off, order_id, sequence, price, ts, quantity, side)
            off += ORDER_RECORD_SIZE
    except (struct.error, ValueError, TypeError):
        return b"".join(
            encode(
                order_id=o.order_id, sequence=o.sequence, price=o.price,
                timestamp_ns=o.timestamp_ns, quantity=o.quantity, side=o.side,
            )
            for o in orders
        )
    return buf


class BatchIPCProducerAdapter:
    """
    No thread, queue or semaphores. Orders are encoded and published to
    the ring on the caller's thread. If the ring is full, the blocking
    wait runs in an executor so the event loop is never blocked.

    submit_many() returns after the orders are PUBLISHED to the ring.
    """

    def __init__(self, ring: FastRing, timeout: float = 1.0):
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self._ring = ring
        self._timeout = timeout
        self.published = 0
        self.queue_wait_seconds = 0.0   # time spent waiting for ring space
        self.publish_seconds = 0.0      # total time inside submit_many
        self._closed = False

    def start(self) -> None:
        pass

    async def submit(self, order) -> bool:
        return (await self.submit_many([order])) == 1

    async def submit_many(self, orders) -> int:
        if self._closed:
            raise RuntimeError("Producer adapter is closed")

        n = len(orders)
        if n == 0:
            return 0

        t0 = time.perf_counter()
        try:
            blob = encode_orders(orders)
        except (TypeError, ValueError) as exc:
            raise ProducerError(str(exc)) from exc

        try:
            self._ring.write_bytes(blob, timeout=0)      # fast, non-blocking
        except RingTimeout as short:
            written = short.written
            wait0 = time.perf_counter()
            try:
                await asyncio.to_thread(
                    self._ring.write_bytes,
                    memoryview(blob)[written * ORDER_RECORD_SIZE:],
                    self._timeout,
                )
            except RingTimeout as exc:
                self.published += written + exc.written
                raise ProducerFull(str(exc)) from exc
            finally:
                self.queue_wait_seconds += time.perf_counter() - wait0

        self.published += n
        self.publish_seconds += time.perf_counter() - t0
        return n

    async def close(self) -> None:
        self._closed = True