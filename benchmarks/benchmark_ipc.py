
"""Simple benchmark for ChronosMatch IPC."""

import argparse
import multiprocessing as mp
import time
import queue

from ipc.consumer import Consumer
from ipc.producer import Producer
from ipc.protocol import BUY
from ipc.ring_buffer import RingBuffer


def producer_worker(buffer, total_orders, results):
    producer = Producer(buffer)
    start = time.perf_counter()

    for order_id in range(1, total_orders + 1):
        producer.submit(
            order_id=order_id,
            sequence=order_id,
            price=5000 + order_id,
            timestamp_ns=order_id * 1000,
            quantity=1,
            side=BUY,
            timeout=30,
        )

    results.put(("producer", time.perf_counter() - start))


def consumer_worker(buffer, total_orders, results):
    consumer = Consumer(buffer)
    received = []
    start = time.perf_counter()

    for _ in range(total_orders):
        received.append(consumer.receive(timeout=30))

    results.put(("consumer", time.perf_counter() - start, received))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--orders", type=int, default=10_000)
    total_orders = parser.parse_args().orders

    if total_orders <= 0:
        parser.error("--orders must be greater than zero")

    context = mp.get_context("spawn")
    buffer = RingBuffer.create()
    results = context.Queue()

    # Share the ring buffer's mapping and synchronization objects.
    producer_buffer = (
        buffer.memory_name,
        buffer.slots_available,
        buffer.items_available,
        buffer.counter_lock,
    )

    def start_worker(target, name, extra_args):
        return context.Process(
            target=target,
            name=name,
            args=(*producer_buffer, *extra_args),
        )

    # Workers attach to the shared buffer inside their own processes.
    producer = context.Process(
        target=run_producer,
        args=(*producer_buffer, total_orders, results),
    )
    consumer = context.Process(
        target=run_consumer,
        args=(*producer_buffer, total_orders, results),
    )

    start = time.perf_counter()

    try:
        consumer.start()
        producer.start()

        producer.join(120)
        consumer.join(120)

        for process in (producer, consumer):
            if process.is_alive():
                process.terminate()
                process.join()
                raise TimeoutError(f"{process.name} timed out")

        if producer.exitcode != 0 or consumer.exitcode != 0:
            raise RuntimeError("A worker process failed")

        measurements = {}
        while True:
            try:
                item = results.get(timeout=1)
                measurements[item[0]] = item
                if len(measurements) == 2:
                    break
            except queue.Empty:
                break

        if "producer" not in measurements or "consumer" not in measurements:
            raise RuntimeError("Missing worker results")

        elapsed = time.perf_counter() - start
        producer_time = measurements["producer"][1]
        consumer_time = measurements["consumer"][1]
        received = measurements["consumer"][2]

        expected_ids = list(range(1, total_orders + 1))
        received_ids = [order[0] for order in received]

        missing = set(expected_ids) - set(received_ids)
        duplicates = len(received_ids) - len(set(received_ids))
        ordering_errors = received_ids != expected_ids

        corrupted = any(
            order[1] != order[0]
            or order[2] != 5000 + order[0]
            or order[3] != order[0] * 1000
            or order[4] != 1
            or order[5] != BUY
            for order in received
        )

        print("\nChronosMatch IPC Benchmark")
        print("--------------------------")
        print(f"Orders requested:      {total_orders}")
        print(f"Orders consumed:       {len(received)}")
        print(f"Total elapsed:         {elapsed:.3f} seconds")
        print(f"Producer time:         {producer_time:.3f} seconds")
        print(f"Consumer time:         {consumer_time:.3f} seconds")
        print(f"Throughput:            {len(received) / elapsed:.2f} orders/second")
        print(f"Missing orders:        {len(missing)}")
        print(f"Duplicate orders:      {duplicates}")
        print(f"Ordering correct:      {not ordering_errors}")
        print(f"Corrupted records:     {corrupted}")

        if (
            len(received) != total_orders
            or missing
            or duplicates
            or ordering_errors
            or corrupted
        ):
            raise AssertionError("Benchmark verification failed")

        print("\nResult: PASS")

    finally:
        for process in (producer, consumer):
            if process.is_alive():
                process.terminate()
                process.join()

        buffer.unlink()
        results.close()


def run_producer(mapping_name, slots, items, lock, total_orders, results):
    buffer = RingBuffer.attach(mapping_name, slots, items, lock)
    try:
        start = time.perf_counter()
        producer = Producer(buffer)

        for order_id in range(1, total_orders + 1):
            producer.submit(
                order_id, order_id, 5000 + order_id,
                order_id * 1000, 1, BUY, timeout=30
            )

        results.put(("producer", time.perf_counter() - start))
    finally:
        buffer.close()


def run_consumer(mapping_name, slots, items, lock, total_orders, results):
    buffer = RingBuffer.attach(mapping_name, slots, items, lock)
    try:
        start = time.perf_counter()
        consumer = Consumer(buffer)
        received = [
            consumer.receive(timeout=30)
            for _ in range(total_orders)
        ]

        results.put(("consumer", time.perf_counter() - start, received))
    finally:
        buffer.close()


if __name__ == "__main__":
    main()
