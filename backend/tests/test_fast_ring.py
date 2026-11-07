
import threading
import pytest

from backend.ipc.fast_ring import FastRing, RingTimeout
from backend.ipc.protocol import decode, encode


def rec(i):
    return encode(order_id=i, sequence=i, price=100,
                  timestamp_ns=i, quantity=1, side=0)


def ids(blob):
    return [decode(blob[i:i + 64])[0] for i in range(0, len(blob), 64)]


def test_fifo_across_wraparound():
    ring = FastRing.create(8)
    try:
        nxt, got = 1, []
        for _ in range(50):
            ring.write_bytes(b"".join(rec(nxt + j) for j in range(5)), timeout=1)
            nxt += 5
            got += ids(ring.read_bytes(8, timeout=1))
        assert got == list(range(1, nxt))
    finally:
        ring.unlink()


def test_read_timeout_when_empty():
    ring = FastRing.create(8)
    try:
        with pytest.raises(RingTimeout):
            ring.read_bytes(4, timeout=0.01)
    finally:
        ring.unlink()


def test_partial_write_is_reported_and_ordered():
    ring = FastRing.create(4)
    try:
        with pytest.raises(RingTimeout) as e:
            ring.write_bytes(b"".join(rec(i) for i in range(1, 7)), timeout=0.01)
        assert e.value.written == 4
        assert ids(ring.read_bytes(8, timeout=1)) == [1, 2, 3, 4]
    finally:
        ring.unlink()


def test_threaded_integrity():
    ring = FastRing.create(1024)
    total, got = 200_000, []

    def reader():
        while len(got) < total:
            got.extend(ids(ring.read_bytes(64, timeout=5)))

    t = threading.Thread(target=reader)
    t.start()
    try:
        i = 1
        while i <= total:
            n = min(100, total - i + 1)
            ring.write_bytes(b"".join(rec(i + j) for j in range(n)), timeout=5)
            i += n
        t.join(30)
        assert got == list(range(1, total + 1))
    finally:
        ring.unlink()