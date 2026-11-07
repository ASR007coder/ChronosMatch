# test / test_ring_buffer_processes.py 


import multiprocessing
import queue

from ipc.ring_buffer import RingBuffer
from ipc.protocol import encode, decode


ORDER_COUNT = 8


def producer(memory_name, slots_available, items_available, counter_lock):
    buffer = RingBuffer.attach(
        memory_name,
        slots_available,
        items_available,
        counter_lock,
    )

    try:
        for i in range(1, ORDER_COUNT + 1):
            record = encode(
                i,          # order_id
                i,          # sequence
                10000 + i,  # price in paise
                100000 + i, # timestamp_ns
                i,          # quantity
                0,          # BUY
            )
            buffer.write(record, timeout=5)

        print("Producer: sent 8 orders")
    finally:
        buffer.close()


def consumer(memory_name, slots_available, items_available, counter_lock, output):
    buffer = RingBuffer.attach(
        memory_name,
        slots_available,
        items_available,
        counter_lock,
    )

    try:
        received = []

        for _ in range(ORDER_COUNT):
            record = buffer.read(timeout=5)
            received.append(decode(record))

        output.put(received)
        print("Consumer: received 8 orders")
    finally:
        buffer.close()


def test_separate_processes():
    context = multiprocessing.get_context("spawn")
    buffer = RingBuffer.create()
    output = context.Queue()

    producer_process = context.Process(
        target=producer,
        args=(
            buffer.memory_name,
            buffer.slots_available,
            buffer.items_available,
            buffer.counter_lock,
        ),
    )

    consumer_process = context.Process(
        target=consumer,
        args=(
            buffer.memory_name,
            buffer.slots_available,
            buffer.items_available,
            buffer.counter_lock,
            output,
        ),
    )

    try:
        consumer_process.start()
        producer_process.start()

        producer_process.join(timeout=15)
        consumer_process.join(timeout=15)

        assert not producer_process.is_alive(), "Producer timed out"
        assert not consumer_process.is_alive(), "Consumer timed out"

        assert producer_process.exitcode == 0, (
            f"Producer failed: {producer_process.exitcode}"
        )
        assert consumer_process.exitcode == 0, (
            f"Consumer failed: {consumer_process.exitcode}"
        )

        received = output.get(timeout=2)

        expected_ids = list(range(1, ORDER_COUNT + 1))
        actual_ids = [order[0] for order in received]

        assert actual_ids == expected_ids, (
            f"Incorrect order sequence: {actual_ids}"
        )

        print("PASS: Separate-process communication")
        print("Received order IDs:", actual_ids)

    finally:
        if producer_process.is_alive():
            producer_process.terminate()
            producer_process.join()

        if consumer_process.is_alive():
            consumer_process.terminate()
            consumer_process.join()

        output.close()
        buffer.close()
        buffer.unlink()


if __name__ == "__main__":
    test_separate_processes()
