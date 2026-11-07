"""IPC integration test: batch integrity and FIFO ordering."""

from threading import Thread

from ipc.ring_buffer import RingBuffer
from ipc.producer import Producer
from ipc.consumer import Consumer


def test_ipc_preserves_order_and_payload_for_batch():
    ring = RingBuffer.create()
    producer = Producer(ring)
    consumer = Consumer(ring)

    expected_orders = [
        {
            "order_id": order_id,
            "sequence": order_id,
            "price": 10000 + order_id,
            "timestamp_ns": 1_000_000 + order_id,
            "quantity": order_id % 10 + 1,
            "side": order_id % 2,
        }
        for order_id in range(1, 101)
    ]

    expected_payloads = [
        (
            order["order_id"],
            order["sequence"],
            order["price"],
            order["timestamp_ns"],
            order["quantity"],
            order["side"],
        )
        for order in expected_orders
    ]

    producer_errors = []

    def produce_batch():
        try:
            for order in expected_orders:
                producer.submit(**order)
        except Exception as exc:
            producer_errors.append(exc)

    producer_thread = Thread(target=produce_batch)
    producer_thread.start()

    try:
        received_orders = [
            consumer.receive(timeout=5)
            for _ in range(len(expected_orders))
        ]

        producer_thread.join(timeout=5)

        assert not producer_thread.is_alive(), (
            "Producer thread did not finish"
        )
        assert not producer_errors, f"Producer failed: {producer_errors}"

        # Verify every payload field and its order.
        assert received_orders == expected_payloads

        # Explicitly verify FIFO sequence ordering.
        received_sequences = [
            order[1]
            for order in received_orders
        ]

        assert received_sequences == list(range(1, 101))

    finally:
        producer_thread.join(timeout=1)
        ring.close()
        ring.unlink()