# test / test_ring_buffer_processes.py 

import unittest

from ipc.ring_buffer import RingBuffer
from ipc.protocol import encode, decode


CAPACITY = 4


def make_order(order_id):
    return encode(
        order_id,
        order_id,
        10000 + order_id,
        100000 + order_id,
        order_id,
        0,
    )


class TestRingBuffer(unittest.TestCase):

    def setUp(self):
        self.buffer = RingBuffer.create()

    def tearDown(self):
        self.buffer.close()
        self.buffer.unlink()

    def test_basic_write_read(self):
        record = make_order(1)

        self.buffer.write(record)
        result = self.buffer.read(timeout=1)

        self.assertEqual(result, record)
        self.assertEqual(decode(result)[0], 1)

    def test_fifo_order(self):
        records = [make_order(i) for i in range(1, CAPACITY + 1)]

        for record in records:
            self.buffer.write(record)

        results = [
            self.buffer.read(timeout=1)
            for _ in range(CAPACITY)
        ]

        self.assertEqual(results, records)

    def test_wraparound(self):
        first_batch = [make_order(i) for i in range(1, 5)]
        second_batch = [make_order(i) for i in range(5, 9)]

        for record in first_batch:
            self.buffer.write(record)

        first_results = [
            self.buffer.read(timeout=1)
            for _ in range(CAPACITY)
        ]

        for record in second_batch:
            self.buffer.write(record)

        second_results = [
            self.buffer.read(timeout=1)
            for _ in range(CAPACITY)
        ]

        results = first_results + second_results
        expected = first_batch + second_batch

        self.assertEqual(results, expected)
        self.assertEqual(
            [decode(record)[0] for record in results],
            list(range(1, 9)),
        )

    def test_empty_buffer_timeout(self):
        with self.assertRaises(TimeoutError):
            self.buffer.read(timeout=0.2)

    def test_full_buffer_timeout(self):
        for i in range(1, CAPACITY + 1):
            self.buffer.write(make_order(i))

        with self.assertRaises(TimeoutError):
            self.buffer.write(make_order(CAPACITY + 1), timeout=0.2)

    def test_write_after_read_from_full_buffer(self):
        for i in range(1, CAPACITY + 1):
            self.buffer.write(make_order(i))

        first = self.buffer.read(timeout=1)

        self.assertEqual(decode(first)[0], 1)

        new_record = make_order(5)
        self.buffer.write(new_record, timeout=1)

        remaining = [
            decode(self.buffer.read(timeout=1))[0]
            for _ in range(CAPACITY)
        ]

        self.assertEqual(remaining, [2, 3, 4, 5])

    def test_invalid_record_is_rejected(self):
        with self.assertRaises((ValueError, TypeError)):
            self.buffer.write(b"invalid")

    def test_operations_after_close_are_rejected(self):
        self.buffer.close()

        with self.assertRaises(RuntimeError):
            self.buffer.write(make_order(1))

        with self.assertRaises(RuntimeError):
            self.buffer.read(timeout=0.1)
    def test_buffer_never_exceeds_capacity(self):
            for i in range(1, CAPACITY + 1):
                self.buffer.write(make_order(i))

            write_counter, read_counter = (
                __import__(
                    "ipc.ring_buffer",
                    fromlist=["METADATA_STRUCT"],
                ).METADATA_STRUCT.unpack_from(self.buffer.memory, 0)
            )

            self.assertEqual(write_counter - read_counter, CAPACITY)

            with self.assertRaises(TimeoutError):
                self.buffer.write(make_order(CAPACITY + 1), timeout=0.1)

if __name__ == "__main__":
    unittest.main(verbosity=2)
