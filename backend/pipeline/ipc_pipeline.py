
# backend/pipeline/ipc_pipeline.py

import asyncio
import threading
import time

from backend.ipc.consumer import Consumer
from backend.ipc.fast_ring import FastRing
from backend.ipc.producer import Producer
from backend.ipc.protocol import ORDER_STRUCT
from backend.ipc.ring_buffer import RingBuffer

from backend.engine.matching_engine import MatchingEngine
from backend.engine.cython.matching_core import CythonMatchingEngine

from backend.monitoring.statistics import calculate_latency_summary

from backend.simulator.batch_adapter import BatchIPCProducerAdapter
from backend.simulator.market_simulator import (
    MarketSimulator,
    SimulatorConfig,
)
from backend.simulator.producer_adapter import IPCProducerAdapter  # noqa: F401


def process_orders(orders: list[dict]) -> dict:
    """Transfer orders through IPC and process them in the matching engine."""

    ring = RingBuffer.create()

    try:
        producer = Producer(ring)
        consumer = Consumer(ring)
        engine = MatchingEngine()

        orders_received = 0
        all_trades = []

        for order in orders:
            producer.submit(
                order_id=order["order_id"],
                sequence=order["sequence"],
                price=order["price"],
                timestamp_ns=order["timestamp_ns"],
                quantity=order["quantity"],
                side=order["side"],
                timeout=1,
            )

            (
                order_id,
                sequence,
                price,
                timestamp_ns,
                quantity,
                side,
            ) = consumer.receive(timeout=1)

            orders_received += 1

            trades = engine.submit(
                order_id=order_id,
                side=side,
                price=price,
                quantity=quantity,
                sequence=sequence,
            )

            for trade in trades:
                all_trades.append({
                    "trade_id": trade[0],
                    "buy_order_id": trade[1],
                    "sell_order_id": trade[2],
                    "price": trade[3],
                    "quantity": trade[4],
                    "sequence": trade[5],
                })

        bids, asks = engine.depth(5)

        return {
            "orders_received": orders_received,
            "orders_processed": engine.orders_processed,
            "trades_executed": engine.trades_executed,
            "trades": all_trades,
            "order_book": {
                "bids": bids,
                "asks": asks,
            },
        }

    finally:
        ring.unlink()


async def run_simulator_pipeline(
    config: SimulatorConfig,
    verify_order_ids: bool = False,
    ring_capacity: int = 16384,
    consumer_batch: int = 1024,
) -> dict:
    """
    Run simulator -> batch adapter -> FastRing -> Cython matching engine.

    Orders are published and consumed in contiguous batches.

    Collects:
    - Pipeline stage timings.
    - Per-order matching-engine submission latency.
    - Optional order-ID integrity verification.
    """

    pipeline_start = time.perf_counter()

    ring = FastRing.create(ring_capacity)
    adapter = BatchIPCProducerAdapter(ring, timeout=1.0)

    producer_done = threading.Event()
    consumer_errors = []
    result = {}

    expected_order_ids = None
    expected_order_count = None

    # Consumer-thread timing counters.
    consumer_receive_seconds = 0.0
    consumer_timeout_seconds = 0.0
    matching_seconds = 0.0
    trade_materialization_seconds = 0.0
    depth_seconds = 0.0
    timeout_count = 0

    # One latency sample per matching-engine submission.
    # Only the consumer thread writes to this list.
    latency_samples_ns = []

    def consume_orders():
        nonlocal consumer_receive_seconds
        nonlocal consumer_timeout_seconds
        nonlocal matching_seconds
        nonlocal trade_materialization_seconds
        nonlocal depth_seconds
        nonlocal timeout_count

        engine = CythonMatchingEngine()

        submit = engine.submit
        read_bytes = ring.read_bytes
        iter_unpack = ORDER_STRUCT.iter_unpack

        perf = time.perf_counter
        perf_ns = time.perf_counter_ns

        raw_trades = []
        extend_trades = raw_trades.extend

        seen = set() if verify_order_ids else None
        orders_received = 0

        try:
            while True:
                t0 = perf()

                try:
                    blob = read_bytes(
                        consumer_batch,
                        timeout=0.05,
                    )

                except TimeoutError:
                    consumer_timeout_seconds += perf() - t0
                    timeout_count += 1

                    # Once the producer is done and the ring is empty,
                    # no additional orders can arrive.
                    if producer_done.is_set() and ring.pending() == 0:
                        break

                    continue

                rows = list(iter_unpack(blob))

                t1 = perf()
                consumer_receive_seconds += t1 - t0

                for (
                    order_id,
                    sequence,
                    price,
                    _ts,
                    quantity,
                    side,
                ) in rows:

                    if (
                        sequence < 1
                        or price <= 0
                        or quantity < 1
                        or side > 1
                    ):
                        raise ValueError("corrupt order record")

                    # Measure one engine submission.
                    latency_start_ns = perf_ns()

                    trades = submit(
                        order_id=order_id,
                        side=side,
                        price=price,
                        quantity=quantity,
                        sequence=sequence,
                    )

                    latency_end_ns = perf_ns()

                    latency_samples_ns.append(
                        latency_end_ns - latency_start_ns
                    )

                    if trades:
                        extend_trades(trades)

                orders_received += len(rows)

                if seen is not None:
                    seen.update(row[0] for row in rows)

                matching_seconds += perf() - t1

            # Materialize trades outside the matching loop.
            materialization_start = perf()

            all_trades = [
                {
                    "trade_id": trade[0],
                    "buy_order_id": trade[1],
                    "sell_order_id": trade[2],
                    "price": trade[3],
                    "quantity": trade[4],
                    "sequence": trade[5],
                }
                for trade in raw_trades
            ]

            trade_materialization_seconds += (
                perf() - materialization_start
            )

            # Capture final order-book depth.
            depth_start = perf()

            bids, asks = engine.depth(5)

            depth_seconds += perf() - depth_start

            result.update({
                "orders_received": orders_received,
                "orders_processed": engine.orders_processed,
                "trades_executed": engine.trades_executed,
                "trades": all_trades,
                "order_book": {
                    "bids": bids,
                    "asks": asks,
                },
                "unique_order_ids": (
                    len(seen) if seen is not None else None
                ),
                "duplicate_order_ids": (
                    orders_received - len(seen)
                    if seen is not None
                    else None
                ),
                "missing_order_ids": (
                    len(expected_order_ids - seen)
                    if expected_order_ids is not None
                    and seen is not None
                    else None
                ),
                "unexpected_order_ids": (
                    len(seen - expected_order_ids)
                    if expected_order_ids is not None
                    and seen is not None
                    else None
                ),
            })

        except BaseException as exc:
            consumer_errors.append(exc)

    consumer_thread = threading.Thread(
        target=consume_orders,
        name="chronosmatch-ipc-consumer",
        daemon=False,
    )

    # Build workload before simulator.run().
    build_start = time.perf_counter()

    simulator = MarketSimulator(
        config=config,
        sink=adapter,
    )

    workload_build_seconds = time.perf_counter() - build_start

    if verify_order_ids:
        expected_order_ids = {
            order.order_id for order in simulator._orders
        }
        expected_order_count = len(simulator._orders)

    stats = None
    adapter_error = None

    adapter_close_seconds = 0.0
    consumer_join_seconds = 0.0
    ring_cleanup_seconds = 0.0

    # Steady-state timing boundary.
    steady_start = time.perf_counter()
    steady_end = steady_start

    try:
        steady_start = time.perf_counter()

        consumer_thread.start()
        adapter.start()

        stats = await simulator.run()

    finally:
        close_start = time.perf_counter()

        try:
            await adapter.close()

        except BaseException as exc:
            adapter_error = exc

        adapter_close_seconds = time.perf_counter() - close_start

        producer_done.set()

        if consumer_thread.ident is not None:
            join_start = time.perf_counter()

            await asyncio.to_thread(consumer_thread.join)

            consumer_join_seconds = time.perf_counter() - join_start

        steady_end = time.perf_counter()

        cleanup_start = time.perf_counter()

        ring.unlink()

        ring_cleanup_seconds = time.perf_counter() - cleanup_start

    if adapter_error is not None:
        raise adapter_error

    if consumer_errors:
        raise RuntimeError(
            "IPC consumer/matching engine failed"
        ) from consumer_errors[0]

    if stats is None:
        raise RuntimeError("Simulator did not complete")

    result["simulator"] = {
        "generated": stats.generated,
        "submitted": stats.submitted,
        "accepted": stats.accepted,
        "rejected": stats.rejected,
        "retried": stats.retried,
        "elapsed_seconds": stats.elapsed_seconds,
        "accepted_rate": stats.accepted_rate,
    }

    result["producer"] = {
        "published": adapter.published,
    }

    # Verify accepted orders were published.
    if adapter.published != stats.accepted:
        raise RuntimeError(
            f"Producer count mismatch: {adapter.published} published, "
            f"{stats.accepted} accepted by simulator"
        )

    # Verify published orders reached the matching engine.
    if result["orders_received"] != adapter.published:
        raise RuntimeError(
            f"Pipeline count mismatch: {result['orders_received']} "
            f"received, {adapter.published} published"
        )

    # Verify the engine processed every published order.
    if result["orders_processed"] != adapter.published:
        raise RuntimeError(
            f"Engine count mismatch: {result['orders_processed']} "
            f"processed, {adapter.published} published"
        )

    # Verify workload IDs are unique and received exactly once.
    if verify_order_ids:
        if len(expected_order_ids) != expected_order_count:
            raise RuntimeError(
                "Generated workload contains duplicate order IDs"
            )

        if result["duplicate_order_ids"] != 0:
            raise RuntimeError(
                f"Duplicate order IDs received: "
                f"{result['duplicate_order_ids']}"
            )

        if result["missing_order_ids"] != 0:
            raise RuntimeError(
                f"Missing order IDs: {result['missing_order_ids']}"
            )

        if result["unexpected_order_ids"] != 0:
            raise RuntimeError(
                f"Unexpected order IDs: {result['unexpected_order_ids']}"
            )

    # Calculate latency statistics outside the measured pipeline interval.
    latency_summary = calculate_latency_summary(latency_samples_ns)

    if latency_summary["count"] != result["orders_processed"]:
        raise RuntimeError(
            f"Latency sample mismatch: {latency_summary['count']} samples "
            f"for {result['orders_processed']} processed orders"
        )

    latency_mean_ns = (
        sum(latency_samples_ns) / len(latency_samples_ns)
        if latency_samples_ns
        else 0.0
    )

    result["latency"] = {
        "count": latency_summary["count"],
        "mean": latency_mean_ns,
        "median": latency_summary["median"],
        "p95": latency_summary["p95"],
        "p99": latency_summary["p99"],
        "max": latency_summary["max"],
    }

    result["consumer_metrics"] = {
        "receive_seconds": consumer_receive_seconds,
        "timeout_seconds": consumer_timeout_seconds,
        "timeout_count": timeout_count,
        "matching_seconds": matching_seconds,
        "trade_materialization_seconds": trade_materialization_seconds,
        "depth_seconds": depth_seconds,
    }

    result["timings"] = {
        "pipeline_wall_seconds": (
            time.perf_counter() - pipeline_start
        ),
        "steady_state_seconds": steady_end - steady_start,
        "workload_build_seconds": workload_build_seconds,
        "simulator_run_seconds": stats.elapsed_seconds,

        "producer_queue_wait_seconds": adapter.queue_wait_seconds,
        "producer_publish_seconds": adapter.publish_seconds,

        "consumer_receive_seconds": consumer_receive_seconds,
        "consumer_timeout_seconds": consumer_timeout_seconds,
        "matching_seconds": matching_seconds,
        "trade_materialization_seconds": trade_materialization_seconds,
        "depth_seconds": depth_seconds,

        "adapter_drain_seconds": adapter_close_seconds,
        "consumer_join_seconds": consumer_join_seconds,
        "ring_cleanup_seconds": ring_cleanup_seconds,
    }

    return result
