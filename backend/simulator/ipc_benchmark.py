
from __future__ import annotations

import argparse
import asyncio
import hashlib
import statistics

from backend.pipeline.ipc_pipeline import run_simulator_pipeline
from backend.simulator.market_simulator import SimulatorConfig
from backend.simulator.workload import WorkloadConfig, MIXED


async def run_one(
    count: int,
    rate: float,
    seed: int,
) -> dict:
    config = SimulatorConfig(
        workload=WorkloadConfig(
            kind=MIXED,
            count=count,
            seed=seed,
        ),
        target_rate_per_sec=rate,
    )

    return await run_simulator_pipeline(
        config,
        verify_order_ids=True,
    )


def trade_stream_hash(result: dict) -> str:
    """SHA-256 over every trade, in order."""

    h = hashlib.sha256()

    for trade in result["trades"]:
        h.update(
            repr((
                trade["trade_id"],
                trade["buy_order_id"],
                trade["sell_order_id"],
                trade["price"],
                trade["quantity"],
                trade["sequence"],
            )).encode()
        )

    return h.hexdigest()


def rates(result: dict) -> tuple[float, float]:
    """Return wall and steady-state throughput in orders/sec."""

    timings = result["timings"]
    processed = result["orders_processed"]

    wall = timings["pipeline_wall_seconds"]
    steady = timings.get("steady_state_seconds") or wall

    wall_rate = processed / wall if wall > 0 else 0.0
    steady_rate = processed / steady if steady > 0 else 0.0

    return wall_rate, steady_rate


def latency_metrics(result: dict) -> dict:
    """
    Return latency metrics.

    Expected units from pipeline: nanoseconds.
    """

    latency = result.get("latency")

    if latency is None:
        raise RuntimeError(
            "Pipeline did not return latency metrics. "
            "Add latency collection to ipc_pipeline.py first."
        )

    required = (
        "count",
        "mean",
        "median",
        "p95",
        "p99",
        "max",
    )

    missing = [key for key in required if key not in latency]

    if missing:
        raise RuntimeError(
            f"Pipeline latency result is missing fields: {missing}"
        )

    return latency


def check_integrity(result: dict) -> dict:
    generated = result["simulator"]["generated"]
    accepted = result["simulator"]["accepted"]
    published = result["producer"]["published"]
    received = result["orders_received"]
    processed = result["orders_processed"]
    unique = result["unique_order_ids"]
    duplicates = result["duplicate_order_ids"]

    latency = latency_metrics(result)

    return {
        "Generated == Accepted": generated == accepted,
        "Accepted == Published": accepted == published,
        "Published == Received": published == received,
        "Received == Processed": received == processed,
        "Received == Unique IDs": received == unique,
        "No duplicate IDs": duplicates == 0,
        "Latency samples == Processed": latency["count"] == processed,
    }


def print_latency(latency: dict) -> None:
    """Display latency values in microseconds."""

    ns_to_us = 1_000

    print("\n=== Latency Metrics ===")
    print(f"Samples collected: {latency['count']:,}")
    print(f"Mean:              {latency['mean'] / ns_to_us:,.2f} us")
    print(f"P50:               {latency['median'] / ns_to_us:,.2f} us")
    print(f"P95:               {latency['p95'] / ns_to_us:,.2f} us")
    print(f"P99:               {latency['p99'] / ns_to_us:,.2f} us")
    print(f"Maximum:           {latency['max'] / ns_to_us:,.2f} us")


def print_stage_timings(timings: dict) -> None:
    print("\n=== Stage Timings ===")

    stages = (
        "workload_build_seconds",
        "simulator_run_seconds",
        "producer_queue_wait_seconds",
        "producer_publish_seconds",
        "consumer_receive_seconds",
        "consumer_timeout_seconds",
        "matching_seconds",
        "trade_materialization_seconds",
        "adapter_drain_seconds",
        "consumer_join_seconds",
    )

    for name in stages:
        if name in timings:
            print(f"{name:35s}: {timings[name]:.6f}s")


def print_integrity(result: dict) -> None:
    print("\n=== Integrity ===")

    checks = check_integrity(result)

    for label, passed in checks.items():
        print(f"{label:35s}: {'PASS' if passed else 'FAIL'}")

    if not all(checks.values()):
        failed = [
            label
            for label, passed in checks.items()
            if not passed
        ]

        raise RuntimeError(
            f"IPC pipeline integrity verification failed: {failed}"
        )


def print_result(result: dict) -> None:
    sim = result["simulator"]
    producer = result["producer"]
    timings = result["timings"]

    generated = sim["generated"]
    accepted = sim["accepted"]
    published = producer["published"]
    received = result["orders_received"]
    processed = result["orders_processed"]
    unique = result["unique_order_ids"]
    duplicates = result["duplicate_order_ids"]

    elapsed = timings["pipeline_wall_seconds"]
    steady = timings.get("steady_state_seconds") or elapsed

    wall_rate, steady_rate = rates(result)
    latency = latency_metrics(result)

    print("\n=== ChronosMatch IPC Pipeline Benchmark ===")

    print(f"Generated:          {generated:,}")
    print(f"Accepted:           {accepted:,}")
    print(f"Published to IPC:   {published:,}")
    print(f"Received by engine: {received:,}")
    print(f"Processed:          {processed:,}")
    print(f"Unique order IDs:   {unique:,}")
    print(f"Duplicate IDs:      {duplicates:,}")
    print(f"Trades executed:    {result['trades_executed']:,}")

    print("\n=== Throughput ===")

    print(
        f"Wall time (incl. workload build): {elapsed:.4f}s "
        f"-> {wall_rate:,.0f} orders/sec"
    )

    print(
        f"Steady-state time:                {steady:.4f}s "
        f"-> {steady_rate:,.0f} orders/sec"
    )

    print_latency(latency)
    print_stage_timings(timings)

    print("\n=== Correctness ===")
    print(f"Trade-stream sha256: {trade_stream_hash(result)[:16]}")

    print_integrity(result)


def print_multi_run_summary(
    steady_rates: list[float],
    wall_rates: list[float],
    p50_values: list[float],
    p95_values: list[float],
    p99_values: list[float],
    hashes: set[str],
) -> None:

    print("\n=== Throughput Summary ===")

    print(
        f"Median steady-state: "
        f"{statistics.median(steady_rates):,.0f} orders/sec"
    )

    print(
        f"Best steady-state:   "
        f"{max(steady_rates):,.0f} orders/sec"
    )

    print(
        f"Worst steady-state:  "
        f"{min(steady_rates):,.0f} orders/sec"
    )

    print(
        f"Median wall:         "
        f"{statistics.median(wall_rates):,.0f} orders/sec"
    )

    print("\n=== Median Latency Across Runs ===")

    print(f"P50: {statistics.median(p50_values):,.2f} us")
    print(f"P95: {statistics.median(p95_values):,.2f} us")
    print(f"P99: {statistics.median(p99_values):,.2f} us")

    print("\n=== Determinism ===")

    print(
        f"Trade hash stable: "
        f"{'PASS' if len(hashes) == 1 else 'FAIL'}"
    )

    if len(hashes) != 1:
        raise RuntimeError("Trade stream differed between runs")


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="ChronosMatch end-to-end IPC benchmark"
    )

    parser.add_argument("--count", type=int, default=100_000)
    parser.add_argument("--rate", type=float, default=1_000_000)
    parser.add_argument("--seed", type=int, default=42)

    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of benchmark repetitions",
    )

    args = parser.parse_args()

    if args.count <= 0:
        parser.error("--count must be positive")

    if args.rate <= 0:
        parser.error("--rate must be positive")

    if args.runs <= 0:
        parser.error("--runs must be positive")

    if args.runs == 1:
        result = await run_one(
            count=args.count,
            rate=args.rate,
            seed=args.seed,
        )

        print_result(result)
        return

    steady_rates = []
    wall_rates = []

    p50_values = []
    p95_values = []
    p99_values = []

    hashes = set()

    for n in range(1, args.runs + 1):
        result = await run_one(
            count=args.count,
            rate=args.rate,
            seed=args.seed,
        )

        checks = check_integrity(result)

        if not all(checks.values()):
            failed = [
                key
                for key, passed in checks.items()
                if not passed
            ]

            raise RuntimeError(
                f"Run {n}: integrity failed: {failed}"
            )

        wall_rate, steady_rate = rates(result)
        digest = trade_stream_hash(result)
        latency = latency_metrics(result)

        wall_rates.append(wall_rate)
        steady_rates.append(steady_rate)

        p50_values.append(latency["median"] / 1_000)
        p95_values.append(latency["p95"] / 1_000)
        p99_values.append(latency["p99"] / 1_000)

        hashes.add(digest)

        print(
            f"Run {n}/{args.runs}: "
            f"steady {steady_rate:>10,.0f}/s  "
            f"P50 {latency['median'] / 1_000:>9,.2f} us  "
            f"P99 {latency['p99'] / 1_000:>9,.2f} us  "
            f"hash {digest[:16]}"
        )

    print_multi_run_summary(
        steady_rates,
        wall_rates,
        p50_values,
        p95_values,
        p99_values,
        hashes,
    )


if __name__ == "__main__":
    asyncio.run(main())
