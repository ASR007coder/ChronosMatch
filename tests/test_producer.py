# tests/test_producer.py



import pytest

from ipc.producer import Producer
from ipc.ring_buffer import RingBuffer
from ipc.protocol import decode, BUY


def test_submit_publishes_order():
    buffer = RingBuffer.create()

    try:
        producer = Producer(buffer)

        result = producer.submit(
            order_id=101,
            sequence=1,
            price=5000,
            timestamp_ns=123456789,
            quantity=10,
            side=BUY,
            timeout=0.1,
        )

        assert result is True

        record = buffer.read(timeout=0.1)
        order = decode(record)

        assert order == (101, 1, 5000, 123456789, 10, BUY)

    finally:
        buffer.unlink()


def test_submit_rejects_invalid_order():
    buffer = RingBuffer.create()

    try:
        producer = Producer(buffer)

        with pytest.raises(ValueError):
            producer.submit(
                order_id=101,
                sequence=0,
                price=5000,
                timestamp_ns=123456789,
                quantity=10,
                side=BUY,
                timeout=0.1,
            )

    finally:
        buffer.unlink()


def test_submit_times_out_when_buffer_is_full():
    buffer = RingBuffer.create()

    try:
        producer = Producer(buffer)

        for order_id in range(1, 5):
            producer.submit(
                order_id=order_id,
                sequence=order_id,
                price=5000,
                timestamp_ns=123456789,
                quantity=10,
                side=BUY,
                timeout=0.1,
            )

        with pytest.raises(TimeoutError):
            producer.submit(
                order_id=5,
                sequence=5,
                price=5000,
                timestamp_ns=123456789,
                quantity=10,
                side=BUY,
                timeout=0.1,
            )

    finally:
        buffer.unlink()
