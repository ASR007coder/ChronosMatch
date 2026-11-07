# ring_buffer.py
import mmap
import struct
import time
import uuid
from multiprocessing import Lock, Semaphore

from backend.ipc.protocol import ORDER_RECORD_SIZE, validate_record


CAPACITY = 64
RECORD_SIZE = ORDER_RECORD_SIZE

METADATA_STRUCT = struct.Struct("<QQ")
METADATA_SIZE = METADATA_STRUCT.size
SLOTS_SIZE = CAPACITY * RECORD_SIZE
SHARED_MEMORY_SIZE = METADATA_SIZE + SLOTS_SIZE


def slot_offset(counter: int) -> int:
    return (counter % CAPACITY) * RECORD_SIZE


def record_offset(counter: int) -> int:
    return METADATA_SIZE + slot_offset(counter)


def is_empty(write_counter: int, read_counter: int) -> bool:
    return write_counter == read_counter


def is_full(write_counter: int, read_counter: int) -> bool:
    return write_counter - read_counter == CAPACITY


class RingBuffer:
    """Single-producer/single-consumer ring buffer using named Windows mmap."""

    def __init__(
        self,
        memory,
        mapping_name,
        slots_available,
        items_available,
        counter_lock,
        owner=False,
    ):
        self.memory = memory
        self.mapping_name = mapping_name
        self.slots_available = slots_available
        self.items_available = items_available
        self.counter_lock = counter_lock
        self.owner = owner
        self.closed = False

    @classmethod
    def create(cls):
        mapping_name = f"ChronosMatch_{uuid.uuid4().hex}"

        memory = mmap.mmap(
            -1,
            SHARED_MEMORY_SIZE,
            tagname=mapping_name,
        )

        METADATA_STRUCT.pack_into(memory, 0, 0, 0)

        return cls(
            memory,
            mapping_name,
            Semaphore(CAPACITY),
            Semaphore(0),
            Lock(),
            owner=True,
        )

    @classmethod
    def attach(
        cls,
        mapping_name,
        slots_available,
        items_available,
        counter_lock,
    ):
        memory = mmap.mmap(
            -1,
            SHARED_MEMORY_SIZE,
            tagname=mapping_name,
        )

        return cls(
            memory,
            mapping_name,
            slots_available,
            items_available,
            counter_lock,
            owner=False,
        )

    @property
    def memory_name(self):
        return self.mapping_name

    def _acquire_many(self, semaphore, count, timeout):
        """Acquire multiple semaphore permits within one timeout window."""

        acquired = 0
        deadline = (
            None if timeout is None
            else time.monotonic() + timeout
        )

        try:
            while acquired < count:
                remaining = (
                    None if deadline is None
                    else max(0.0, deadline - time.monotonic())
                )

                if not semaphore.acquire(timeout=remaining):
                    break

                acquired += 1

        except BaseException:
            for _ in range(acquired):
                semaphore.release()
            raise

        if acquired != count:
            for _ in range(acquired):
                semaphore.release()
            return False

        return True

    def write(self, record, timeout=None):
        """Write one 64-byte record."""

        if self.closed:
            raise RuntimeError("Ring buffer is closed")

        validate_record(record)

        if not self.slots_available.acquire(timeout=timeout):
            raise TimeoutError("Timed out waiting for a free slot")

        committed = False

        try:
            with self.counter_lock:
                write_counter, read_counter = (
                    METADATA_STRUCT.unpack_from(self.memory, 0)
                )

                if write_counter - read_counter >= CAPACITY:
                    raise RuntimeError(
                        "Semaphore/counter state is inconsistent"
                    )

                offset = record_offset(write_counter)

                self.memory[offset:offset + RECORD_SIZE] = record

                METADATA_STRUCT.pack_into(
                    self.memory,
                    0,
                    write_counter + 1,
                    read_counter,
                )

                committed = True

            self.items_available.release()

        except BaseException:
            if not committed:
                self.slots_available.release()
            raise

    def read(self, timeout=None):
        """Read one 64-byte record."""

        if self.closed:
            raise RuntimeError("Ring buffer is closed")

        if not self.items_available.acquire(timeout=timeout):
            raise TimeoutError("Timed out waiting for an order")

        committed = False

        try:
            with self.counter_lock:
                write_counter, read_counter = (
                    METADATA_STRUCT.unpack_from(self.memory, 0)
                )

                if write_counter <= read_counter:
                    raise RuntimeError(
                        "Semaphore/counter state is inconsistent"
                    )

                offset = record_offset(read_counter)

                record = self.memory[
                    offset:offset + RECORD_SIZE
                ]

                METADATA_STRUCT.pack_into(
                    self.memory,
                    0,
                    write_counter,
                    read_counter + 1,
                )

                committed = True

            self.slots_available.release()

            return record

        except BaseException:
            if not committed:
                self.items_available.release()
            raise

    def write_many(self, records, timeout=None):
        """
        Atomically publish multiple records.

        All requested slots must be acquired before anything is published.
        """

        if self.closed:
            raise RuntimeError("Ring buffer is closed")

        records = list(records)

        if not records:
            return 0

        if len(records) > CAPACITY:
            raise ValueError(
                f"Batch cannot exceed ring capacity ({CAPACITY})"
            )

        for record in records:
            validate_record(record)

        count = len(records)

        if not self._acquire_many(
            self.slots_available,
            count,
            timeout,
        ):
            raise TimeoutError("Timed out waiting for free slots")

        committed = False

        try:
            with self.counter_lock:
                write_counter, read_counter = (
                    METADATA_STRUCT.unpack_from(self.memory, 0)
                )

                if write_counter - read_counter + count > CAPACITY:
                    raise RuntimeError(
                        "Semaphore/counter state is inconsistent"
                    )

                for index, record in enumerate(records):
                    offset = record_offset(write_counter + index)

                    self.memory[
                        offset:offset + RECORD_SIZE
                    ] = record

                METADATA_STRUCT.pack_into(
                    self.memory,
                    0,
                    write_counter + count,
                    read_counter,
                )

                committed = True

            for _ in range(count):
                self.items_available.release()

            return count

        except BaseException:
            if not committed:
                for _ in range(count):
                    self.slots_available.release()
            raise

    def read_many(self, max_records=CAPACITY, timeout=None):
        """
        Read at least one record, then consume up to max_records
        currently available records.
        """

        if self.closed:
            raise RuntimeError("Ring buffer is closed")

        if (
            isinstance(max_records, bool)
            or not isinstance(max_records, int)
        ):
            raise TypeError("max_records must be an integer")

        if not 1 <= max_records <= CAPACITY:
            raise ValueError(
                f"max_records must be between 1 and {CAPACITY}"
            )

        if not self.items_available.acquire(timeout=timeout):
            raise TimeoutError("Timed out waiting for an order")

        acquired = 1

        try:
            while acquired < max_records:
                if not self.items_available.acquire(block=False):
                    break

                acquired += 1

        except BaseException:
            for _ in range(acquired):
                self.items_available.release()
            raise

        committed = False

        try:
            with self.counter_lock:
                write_counter, read_counter = (
                    METADATA_STRUCT.unpack_from(self.memory, 0)
                )

                available = write_counter - read_counter

                if available < acquired:
                    raise RuntimeError(
                        "Semaphore/counter state is inconsistent"
                    )

                records = []

                for index in range(acquired):
                    offset = record_offset(read_counter + index)

                    records.append(
                        self.memory[
                            offset:offset + RECORD_SIZE
                        ]
                    )

                METADATA_STRUCT.pack_into(
                    self.memory,
                    0,
                    write_counter,
                    read_counter + acquired,
                )

                committed = True

            for _ in range(acquired):
                self.slots_available.release()

            return records

        except BaseException:
            if not committed:
                for _ in range(acquired):
                    self.items_available.release()
            raise

    def close(self):
        if not self.closed:
            self.memory.close()
            self.closed = True

    def unlink(self):
        """Close the mapping. Windows releases it when handles close."""

        if not self.owner:
            raise RuntimeError(
                "Only the owner may unlink shared memory"
            )

        self.close()
