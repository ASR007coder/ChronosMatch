# tests/test_ipc_stress.py

import multiprocessing as mp
import time

from ipc.consumer import Consumer
from ipc.producer import Producer
from ipc.protocol import BUY
from ipc.ring_buffer import RingBuffer


TOTAL_ORDERS = 10_000
CONSUMER_TIMEOUT = 30


def producer_worker(
    mapping_name,
    slots_available,
    items_available,
    counter_lock,
    accepted_ids,
    errors,
):
    buffer = RingBuffer.attach(
        mapping_name,
        slots_available,
        items_available,
        counter_lock,
    )

    try:
        producer = Producer(buffer)

        for order_id in range(1, TOTAL_ORDERS + 1):
            producer.submit(
                order_id=order_id,
                sequence=order_id,
                price=5000 + order_id,
                timestamp_ns=order_id * 1000,
                quantity=1,
                side=BUY,
                timeout=30,
            )

            # Record only after submit() confirms publication.
            accepted_ids.append(order_id)

    except BaseException as exc:
        errors.put(("producer", repr(exc)))
    finally:
        buffer.close()


def consumer_worker(
    mapping_name,
    slots_available,
    items_available,
    counter_lock,
    received_orders,
    errors,
):
    buffer = RingBuffer.attach(
        mapping_name,
        slots_available,
        items_available,
        counter_lock,
    )

    try:
        consumer = Consumer(buffer)

        for _ in range(TOTAL_ORDERS):
            order = consumer.receive(timeout=CONSUMER_TIMEOUT)
            received_orders.append(order)

    except BaseException as exc:
        errors.put(("consumer", repr(exc)))
    finally:
        buffer.close()


def test_10000_orders_between_separate_processes():
    ctx = mp.get_context("spawn")

    buffer = RingBuffer.create()
    manager = ctx.Manager()

    accepted_ids = manager.list()
    received_orders = manager.list()
    errors = ctx.Queue()

    producer = ctx.Process(
        target=producer_worker,
        args=(
            buffer.memory_name,
            buffer.slots_available,
            buffer.items_available,
            buffer.counter_lock,
            accepted_ids,
            errors,
        ),
    )

    consumer = ctx.Process(
        target=consumer_worker,
        args=(
            buffer.memory_name,
            buffer.slots_available,
            buffer.items_available,
            buffer.counter_lock,
            received_orders,
            errors,
        ),
    )

    try:
        # Start the consumer first so it is ready to receive.
        consumer.start()
        producer.start()

        producer.join(timeout=120)
        consumer.join(timeout=120)

        if producer.is_alive():
            producer.terminate()
            producer.join()
            raise AssertionError("Producer did not terminate in time")

        if consumer.is_alive():
            consumer.terminate()
            consumer.join()
            raise AssertionError("Consumer did not terminate in time")

        reported_errors = []
        while not errors.empty():
            reported_errors.append(errors.get())

        assert not reported_errors, f"Worker errors: {reported_errors}"
        assert producer.exitcode == 0
        assert consumer.exitcode == 0

        accepted = list(accepted_ids)
        received = list(received_orders)

        received_ids = [order[0] for order in received]
        expected_ids = list(range(1, TOTAL_ORDERS + 1))

        missing = sorted(set(accepted) - set(received_ids))
        duplicates = len(received_ids) - len(set(received_ids))
        ordering_errors = [
            (index, expected, actual)
            for index, (expected, actual)
            in enumerate(zip(accepted, received_ids))
            if expected != actual
        ]

        corrupted = [
            order for order in received
            if order[1] != order[0]
            or order[2] != 5000 + order[0]
            or order[3] != order[0] * 1000
            or order[4] != 1
            or order[5] != BUY
        ]

        print(f"Accepted: {len(accepted)}")
        print(f"Consumed: {len(received)}")
        print(f"Missing IDs: {len(missing)}")
        print(f"Duplicate IDs: {duplicates}")
        print(f"Ordering errors: {len(ordering_errors)}")
        print(f"Corrupted records: {len(corrupted)}")

        assert accepted == expected_ids
        assert received_ids == accepted
        assert not missing
        assert duplicates == 0
        assert not ordering_errors
        assert not corrupted

    finally:
        if producer.is_alive():
            producer.terminate()
            producer.join()

        if consumer.is_alive():
            consumer.terminate()
            consumer.join()

        buffer.unlink()
        manager.shutdown()
