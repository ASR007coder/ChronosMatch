# ipc / ring_buffer.py 


import mmap
import struct
import uuid
from multiprocessing import Lock, Semaphore

from ipc.protocol import ORDER_RECORD_SIZE, validate_record


CAPACITY = 4
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
        self, memory, mapping_name, slots_available,
        items_available, counter_lock, owner=False
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
        # Windows named mappings let other processes open the same region.
        mapping_name = f"ChronosMatch_{uuid.uuid4().hex}"
        memory = mmap.mmap(
            -1, SHARED_MEMORY_SIZE, tagname=mapping_name
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
        cls, mapping_name, slots_available,
        items_available, counter_lock
    ):
        # Open the existing named mapping; do not initialize its counters.
        memory = mmap.mmap(
            -1, SHARED_MEMORY_SIZE, tagname=mapping_name
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

    def write(self, record, timeout=None):
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

                # The order is now committed to shared memory.
                committed = True

            self.items_available.release()

        except BaseException:
            # Restore the slot only if no order was committed.
            if not committed:
                self.slots_available.release()
            raise

    def read(self, timeout=None):
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
                record = self.memory[offset:offset + RECORD_SIZE]

                METADATA_STRUCT.pack_into(
                    self.memory,
                    0,
                    write_counter,
                    read_counter + 1,
                )

                # The order has now been consumed.
                committed = True

            self.slots_available.release()
            return record

        except BaseException:
            # Restore the item only if it was not consumed.
            if not committed:
                self.items_available.release()
            raise

    def close(self):
        if not self.closed:
            self.memory.close()
            self.closed = True

    def unlink(self):
        # Windows named mappings are released when handles close.
        # There is no POSIX-style unlink operation for this mapping.
        if not self.owner:
            raise RuntimeError("Only the owner may unlink shared memory")
        self.close()
