"""Concurrent ring-buffer test: FIFO, payload integrity, and no deadlock."""

from threading import Thread

import pytest

from backend.ipc.protocol import encode, decode
from backend.ipc.ring_buffer import RingBuffer


def test_ring_buffer_concurrent_batch_preserves_all_records():
    ring = RingBuffer.create()

    total_orders = 200
    received_records = []
    producer_errors = []
    consumer_errors = []

    expected_records = [
        encode(
            order_id=i,
            sequence=i,
            price=10_000 + i,
            timestamp_ns=1_000_000 + i,
            quantity=(i % 100) + 1,
            side=i % 2,
        )
        for i in range(1, total_orders + 1)
    ]

    def producer_task():
        try:
            for record in expected_records:
                ring.write(record, timeout=2)
        except BaseException as exc:
            producer_errors.append(exc)

    def consumer_task():
        try:
            for _ in range(total_orders):
                record = ring.read(timeout=2)
                received_records.append(record)
        except BaseException as exc:
            consumer_errors.append(exc)

    producer = Thread(target=producer_task, daemon=True)
    consumer = Thread(target=consumer_task, daemon=True)

    try:
        consumer.start()
        producer.start()

        producer.join(timeout=10)
        consumer.join(timeout=10)

        assert not producer.is_alive(), "Producer thread did not finish"
        assert not consumer.is_alive(), "Consumer thread did not finish"

        assert producer_errors == []
        assert consumer_errors == []

        # Every record must arrive exactly as written.
        assert received_records == expected_records

        # Verify decoded sequence and payload fields.
        decoded_records = [decode(record) for record in received_records]

        sequences = [record[1] for record in decoded_records]
        assert sequences == list(range(1, total_orders + 1))

        order_ids = [record[0] for record in decoded_records]
        assert order_ids == list(range(1, total_orders + 1))

    finally:
        ring.close()
        ring.unlink()