
"""Benchmark for the ChronosMatch IPC pipeline."""

import argparse
import multiprocessing as mp
import queue
import time

from backend.ipc.protocol import BUY
from backend.ipc.ring_buffer import RingBuffer


WORKER_TIMEOUT = 120
RESULT_POLL_INTERVAL = 1


def run_producer(
    mapping_name,
    slots_available,
    items_available,
    counter_lock,
    total_orders,
    results,
):
    """Attach to shared memory and submit orders."""
    buffer = RingBuffer.attach(
        mapping_name,
        slots_available,
        items_available,
        counter_lock,
    )

    try:
        # Import inside the worker so it can be initialized independently.
        from backend.ipc.producer import Producer

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

        elapsed = time.perf_counter() - start
        results.put(("producer", elapsed))

    finally:
        buffer.close()


def run_consumer(
    mapping_name,
    slots_available,
    items_available,
    counter_lock,
    total_orders,
    results,
):
    """Attach to shared memory and receive orders."""
    buffer = RingBuffer.attach(
        mapping_name,
        slots_available,
        items_available,
        counter_lock,
    )

    try:
        from backend.ipc.consumer import Consumer

        consumer = Consumer(buffer)
        received = []
        start = time.perf_counter()

        for _ in range(total_orders):
            received.append(consumer.receive(timeout=30))

        elapsed = time.perf_counter() - start

        # Send the received orders to the parent. The parent must drain
        # this queue while workers run to avoid a queue/join deadlock.
        results.put(("consumer", elapsed, received))

    finally:
        buffer.close()


def collect_results(results, processes, timeout):
    """Collect worker results while checking for timeouts and failures."""
    measurements = {}
    deadline = time.monotonic() + timeout

    while len(measurements) < 2:
        remaining = deadline - time.monotonic()

        if remaining <= 0:
            alive = [
                process.name
                for process in processes
                if process.is_alive()
            ]
            raise TimeoutError(
                f"Timed out waiting for worker results. "
                f"Still running: {alive}"
            )

        try:
            item = results.get(
                timeout=min(RESULT_POLL_INTERVAL, remaining)
            )
            measurements[item[0]] = item

        except queue.Empty:
            failed = [
                (process.name, process.exitcode)
                for process in processes
                if process.exitcode not in (None, 0)
            ]

            if failed:
                raise RuntimeError(
                    f"Worker process failure: {failed}"
                )

            if all(not process.is_alive() for process in processes):
                break

    return measurements


def verify_results(received, total_orders):
    """Check order count, IDs, sequence, ordering, and data integrity."""
    expected_ids = list(range(1, total_orders + 1))
    received_ids = [order[0] for order in received]

    missing = set(expected_ids) - set(received_ids)
    duplicates = len(received_ids) - len(set(received_ids))
    ordering_correct = received_ids == expected_ids

    corrupted = any(
        order[1] != order[0]
        or order[2] != 5000 + order[0]
        or order[3] != order[0] * 1000
        or order[4] != 1
        or order[5] != BUY
        for order in received
    )

    passed = (
        len(received) == total_orders
        and not missing
        and duplicates == 0
        and ordering_correct
        and not corrupted
    )

    return {
        "missing": len(missing),
        "duplicates": duplicates,
        "ordering_correct": ordering_correct,
        "corrupted": corrupted,
        "passed": passed,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark ChronosMatch shared-memory IPC."
    )
    parser.add_argument(
        "--orders",
        type=int,
        default=10_000,
        help="Number of orders to transfer (default: 10000)",
    )
    args = parser.parse_args()
    total_orders = args.orders

    if total_orders <= 0:
        parser.error("--orders must be greater than zero")

    context = mp.get_context("spawn")
    buffer = RingBuffer.create()
    results = context.Queue()

    shared_buffer_args = (
        buffer.memory_name,
        buffer.slots_available,
        buffer.items_available,
        buffer.counter_lock,
    )

    producer = context.Process(
        target=run_producer,
        name="IPC-Producer",
        args=(*shared_buffer_args, total_orders, results),
    )
    consumer = context.Process(
        target=run_consumer,
        name="IPC-Consumer",
        args=(*shared_buffer_args, total_orders, results),
    )

    start = time.perf_counter()

    try:
        # Start the consumer first so it is ready to drain the buffer.
        consumer.start()
        producer.start()

        # Important: read results before joining workers. The consumer
        # sends the entire received-order list through this queue.
        measurements = collect_results(
            results,
            (producer, consumer),
            WORKER_TIMEOUT,
        )

        # Worker results have been drained; now wait for process exit.
        for process in (producer, consumer):
            process.join(timeout=5)

            if process.is_alive():
                raise TimeoutError(
                    f"{process.name} did not exit after sending results"
                )

            if process.exitcode != 0:
                raise RuntimeError(
                    f"{process.name} exited with code {process.exitcode}"
                )

        if "producer" not in measurements or "consumer" not in measurements:
            raise RuntimeError(
                f"Missing worker results: {list(measurements.keys())}"
            )

        elapsed = time.perf_counter() - start
        producer_time = measurements["producer"][1]
        consumer_time = measurements["consumer"][1]
        received = measurements["consumer"][2]

        verification = verify_results(received, total_orders)
        throughput = len(received) / elapsed if elapsed > 0 else 0

        print("\nChronosMatch IPC Benchmark")
        print("--------------------------")
        print(f"Orders requested:      {total_orders}")
        print(f"Orders consumed:       {len(received)}")
        print(f"Total elapsed:         {elapsed:.3f} seconds")
        print(f"Producer time:         {producer_time:.3f} seconds")
        print(f"Consumer time:         {consumer_time:.3f} seconds")
        print(f"Throughput:            {throughput:.2f} orders/second")
        print(f"Missing orders:        {verification['missing']}")
        print(f"Duplicate orders:      {verification['duplicates']}")
        print(f"Ordering correct:      {verification['ordering_correct']}")
        print(f"Corrupted records:     {verification['corrupted']}")

        if not verification["passed"]:
            raise AssertionError("Benchmark verification failed")

        print("\nResult: PASS")

    finally:
        # Stop remaining workers before releasing shared resources.
        for process in (producer, consumer):
            if process.pid is not None and process.is_alive():
                process.terminate()
                process.join(timeout=5)

        # Close queue resources even if the benchmark fails.
        results.cancel_join_thread()
        results.close()

        buffer.unlink()


if __name__ == "__main__":
    main()
