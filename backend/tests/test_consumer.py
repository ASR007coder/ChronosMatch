# test/test_consumer.py


import pytest

from ipc.consumer import Consumer
from ipc.producer import Producer
from ipc.ring_buffer import RingBuffer
from ipc.protocol import BUY


def test_consumer_receives_submitted_order():
    buffer = RingBuffer.create()

    try:
        producer = Producer(buffer)
        consumer = Consumer(buffer)

        producer.submit(
            order_id=101,
            sequence=1,
            price=5000,
            timestamp_ns=123456789,
            quantity=10,
            side=BUY,
            timeout=0.1,
        )

        order = consumer.receive(timeout=0.1)

        assert order == (101, 1, 5000, 123456789, 10, BUY)

    finally:
        buffer.unlink()


def test_consumer_times_out_when_buffer_is_empty():
    buffer = RingBuffer.create()

    try:
        consumer = Consumer(buffer)

        with pytest.raises(TimeoutError):
            consumer.receive(timeout=0.1)

    finally:
        buffer.unlink()

