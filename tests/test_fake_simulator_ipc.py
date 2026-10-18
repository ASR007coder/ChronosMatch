# tests/test_fake_simulator_ipc.py 

import time

from ipc.consumer import Consumer
from ipc.producer import Producer
from ipc.protocol import BUY
from ipc.ring_buffer import RingBuffer


def test_producer_to_consumer():
    ring = RingBuffer.create()

    try:
        producer = Producer(ring)
        consumer = Consumer(ring)

        expected_order = (
            1,             # order_id
            1,             # sequence
            10000,         # price in paise
            time.time_ns(),
            5,             # quantity
            BUY,
        )

        producer.submit(
            order_id=expected_order[0],
            sequence=expected_order[1],
            price=expected_order[2],
            timestamp_ns=expected_order[3],
            quantity=expected_order[4],
            side=expected_order[5],
        )

        received_order = consumer.receive(timeout=1)

        assert received_order == expected_order

    finally:
        ring.unlink()
