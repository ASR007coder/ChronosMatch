"""
ChronosMatch — Market Simulator
Load-testing / benchmark script.

Runs the simulator at multiple scales and reports throughput.

Usage:
    python -m simulator.benchmark                # default scales
    python -m simulator.benchmark --count 10000  # single scale
"""

from __future__ import annotations

import argparse
import asyncio
import time

from simulator.market_simulator import (
    InMemorySink,
    MarketSimulator,
    SimulatorConfig,
)
from simulator.workload import MIXED, WorkloadConfig


DEFAULT_SCALES = (1_000, 10_000, 100_000)


async def run_one(count: int, rate_per_sec: float = 1_000_000.0,
                  seed: int = 42) -> dict:
    """Run one benchmark at the given scale. Returns a dict of results."""
    cfg = SimulatorConfig(
        workload=WorkloadConfig(kind=MIXED, count=count, seed=seed),
        target_rate_per_sec=rate_per_sec,
    )
    sink = InMemorySink()
    sim = MarketSimulator(cfg, sink)

    wall_start = time.perf_counter()
    stats = await sim.run()
    wall_elapsed = time.perf_counter() - wall_start

    # Sanity checks
    ids = [o.order_id for o in sink.orders]
    unique_ids = len(set(ids))
    missing = count - unique_ids

    return {
        "count": count,
        "generated": stats.generated,
        "submitted": stats.submitted,
        "accepted": stats.accepted,
        "rejected": stats.rejected,
        "retried": stats.retried,
        "elapsed": wall_elapsed,
        "accepted_rate": stats.accepted / wall_elapsed if wall_elapsed > 0 else 0,
        "unique_ids": unique_ids,
        "missing": missing,
    }


async def run_all(scales, rate_per_sec, seed) -> None:
    print(f"=== ChronosMatch simulator benchmark ===")
    print(f"scales: {scales}")
    print(f"target rate: {rate_per_sec:,.0f}/s  seed={seed}")
    print()
    print(f"{'count':>10} {'accepted':>10} {'elapsed_s':>10} {'rate/s':>12} "
          f"{'rejected':>9} {'missing':>8}")
    print("-" * 66)

    for scale in scales:
        result = await run_one(scale, rate_per_sec, seed)
        print(
            f"{result['count']:>10,} "
            f"{result['accepted']:>10,} "
            f"{result['elapsed']:>10.3f} "
            f"{result['accepted_rate']:>12,.0f} "
            f"{result['rejected']:>9,} "
            f"{result['missing']:>8,}"
        )

    print()
    print("Done.")


def _parse_args():
    p = argparse.ArgumentParser(description="ChronosMatch simulator benchmark")
    p.add_argument("--count", type=int, default=None,
                   help="run a single count instead of the default scales")
    p.add_argument("--rate", type=float, default=1_000_000.0,
                   help="target rate per second (default: 1,000,000)")
    p.add_argument("--seed", type=int, default=42,
                   help="RNG seed for reproducibility")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    scales = (args.count,) if args.count else DEFAULT_SCALES
    asyncio.run(run_all(scales, args.rate, args.seed))


if __name__ == "__main__":
    main()