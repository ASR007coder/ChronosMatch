import mmap
import struct
import time
import uuid

from backend.ipc.protocol import ORDER_RECORD_SIZE

RECORD_SIZE = ORDER_RECORD_SIZE
WRITE_OFF = 0        # producer-owned counter, own cache line
READ_OFF = 64        # consumer-owned counter, own cache line
HEADER_SIZE = 128

_U64 = struct.Struct("<Q")
_u64_unpack = _U64.unpack_from
_u64_pack = _U64.pack_into
_sleep = time.sleep


class RingTimeout(TimeoutError):
    def __init__(self, message, written=0):
        super().__init__(message)
        self.written = written


class FastRing:
    """
    Lock-free SPSC ring of 64-byte records, moved in whole batches.

    Each side writes only its own counter. Data is written before the
    write counter is published and read before the read counter is
    published. No semaphores, no lock.
    """

    def __init__(self, memory, name, capacity, owner=False):
        if capacity < 4 or capacity & (capacity - 1):
            raise ValueError("capacity must be a power of two >= 4")
        self.memory = memory
        self.name = name
        self.capacity = capacity
        self.mask = capacity - 1
        self.owner = owner
        self.closed = False
        # Producer-side local state / consumer-side local state.
        self._w = _u64_unpack(memory, WRITE_OFF)[0]
        self._r = _u64_unpack(memory, READ_OFF)[0]

    @classmethod
    def create(cls, capacity=16384):
        name = f"ChronosFast_{uuid.uuid4().hex}"
        size = HEADER_SIZE + capacity * RECORD_SIZE
        memory = mmap.mmap(-1, size, tagname=name)
        _u64_pack(memory, WRITE_OFF, 0)
        _u64_pack(memory, READ_OFF, 0)
        return cls(memory, name, capacity, owner=True)

    @classmethod
    def attach(cls, name, capacity):
        size = HEADER_SIZE + capacity * RECORD_SIZE
        memory = mmap.mmap(-1, size, tagname=name)
        return cls(memory, name, capacity, owner=False)

    # ---------------- producer side ----------------

    def _wait_space(self, w, need, deadline, done):
        spins = 0
        while True:
            r = _u64_unpack(self.memory, READ_OFF)[0]
            free = self.capacity - (w - r)
            if free >= need:
                return free
            if deadline is not None and time.monotonic() >= deadline:
                raise RingTimeout(
                    "Timed out waiting for ring space", written=done
                )
            spins += 1
            _sleep(0 if spins <= 64 else 0.0005)

    def write_bytes(self, blob, timeout=None):
        """
        Publish N*64 bytes in FIFO order. Returns N.
        timeout=0 means a non-blocking attempt.
        On timeout raises RingTimeout; .written records already published.
        """
        mv = memoryview(blob)
        if mv.ndim != 1 or mv.format != "B":
            mv = mv.cast("B")
        if mv.nbytes % RECORD_SIZE:
            raise ValueError("blob length must be a multiple of 64")

        n = mv.nbytes // RECORD_SIZE
        if n == 0:
            return 0

        mem = self.memory
        cap = self.capacity
        mask = self.mask
        w = self._w
        deadline = None if timeout is None else time.monotonic() + timeout
        quarter = cap >> 2
        done = 0

        while done < n:
            r = _u64_unpack(mem, READ_OFF)[0]
            free = cap - (w - r)
            need = min(n - done, quarter)
            if free < need:
                free = self._wait_space(w, need, deadline, done)

            k = min(free, n - done)
            start = w & mask
            first = min(k, cap - start)
            off = HEADER_SIZE + start * RECORD_SIZE

            mem[off:off + first * RECORD_SIZE] = mv[
                done * RECORD_SIZE:(done + first) * RECORD_SIZE
            ]
            if first < k:
                mem[HEADER_SIZE:HEADER_SIZE + (k - first) * RECORD_SIZE] = mv[
                    (done + first) * RECORD_SIZE:(done + k) * RECORD_SIZE
                ]

            w += k
            self._w = w
            _u64_pack(mem, WRITE_OFF, w)   # publish after data is in place
            done += k

        return n

    # ---------------- consumer side ----------------

    def _wait_items(self, r, deadline):
        spins = 0
        while True:
            w = _u64_unpack(self.memory, WRITE_OFF)[0]
            if w != r:
                return w
            if deadline is not None and time.monotonic() >= deadline:
                raise RingTimeout("Timed out waiting for an order")
            spins += 1
            _sleep(0 if spins <= 64 else 0.0005)

    def read_bytes(self, max_records=1024, timeout=None):
        """Block until >=1 record exists; return up to max_records*64 bytes."""
        if max_records < 1:
            raise ValueError("max_records must be >= 1")

        mem = self.memory
        r = self._r
        w = _u64_unpack(mem, WRITE_OFF)[0]
        if w == r:
            deadline = None if timeout is None else time.monotonic() + timeout
            w = self._wait_items(r, deadline)

        n = min(w - r, max_records)
        start = r & self.mask
        first = min(n, self.capacity - start)
        off = HEADER_SIZE + start * RECORD_SIZE

        if first == n:
            blob = mem[off:off + n * RECORD_SIZE]
        else:
            blob = (
                mem[off:off + first * RECORD_SIZE]
                + mem[HEADER_SIZE:HEADER_SIZE + (n - first) * RECORD_SIZE]
            )

        r += n
        self._r = r
        _u64_pack(mem, READ_OFF, r)        # publish only after the copy
        return blob

    def pending(self):
        return (
            _u64_unpack(self.memory, WRITE_OFF)[0]
            - _u64_unpack(self.memory, READ_OFF)[0]
        )

    def close(self):
        if not self.closed:
            self.memory.close()
            self.closed = True

    def unlink(self):
        if not self.owner:
            raise RuntimeError("Only the owner may unlink shared memory")
        self.close()