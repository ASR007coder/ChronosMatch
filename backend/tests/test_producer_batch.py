
import pytest

from ipc.producer import Producer
from ipc.ring_buffer import RingBuffer
from ipc.protocol import decode


@pytest.fixture
def setup_producer():
    ring = RingBuffer.create()
    producer = Producer(ring)

    yield producer, ring

    ring.unlink()


def make_order(order_id):
    return (
        order_id,
        order_id,
        10000 + order_id,
        100000 + order_id,
        order_id,
        0,
    )


def test_submit_many(setup_producer):
    producer, ring = setup_producer

    orders = [make_order(i) for i in range(1, 5)]

    assert producer.submit_many(orders, timeout=1) == 4

    records = ring.read_many(4, timeout=1)

    assert [decode(record)[0] for record in records] == [1, 2, 3, 4]


def test_submit_many_empty_batch(setup_producer):
    producer, ring = setup_producer

    assert producer.submit_many([]) == 0
    with pytest.raises(TimeoutError):
        ring.read(timeout=0.05)


def test_submit_many_invalid_order_publishes_nothing(setup_producer):
    producer, ring = setup_producer

    orders = [
        make_order(1),
        (2, 2, "invalid-price", 100002, 2, 0),
    ]

    with pytest.raises((TypeError, ValueError)):
        producer.submit_many(orders)

    with pytest.raises(TimeoutError):
        ring.read(timeout=0.05)


def test_submit_many_preserves_existing_submit(setup_producer):
    producer, ring = setup_producer

    assert producer.submit(*make_order(1)) is True

    assert producer.submit_many(
        [make_order(2), make_order(3)],
        timeout=1,
    ) == 2

    records = ring.read_many(3, timeout=1)

    assert [decode(record)[0] for record in records] == [1, 2, 3]
