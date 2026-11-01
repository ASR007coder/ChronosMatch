"""
ChronosMatch — Market Simulator
Load-testing / benchmark script.
"""
from __future__ import annotations

import argparse
import asyncio
import time

from simulator.market_simulator import InMemorySink, MarketSimulator, SimulatorConfig
from simulator.workload import MIXED, WorkloadConfig, build_workload

DEFAULT_SCALES = (1_000, 10_000, 100_000)

async def run_one(count: int, rate_per_sec: float = 1_000_000.0, seed: int = 42) -> dict:
    gen_start = time.perf_counter()
    workload_cfg = WorkloadConfig(kind=MIXED, count=count, seed=seed)
    _ = build_workload(workload_cfg)
    gen_elapsed = time.perf_counter() - gen_start

    cfg = SimulatorConfig(workload=workload_cfg, target_rate_per_sec=rate_per_sec)
    sink = InMemorySink()
    sim = MarketSimulator(cfg, sink)

    wall_start = time.perf_counter()
    stats = await sim.run()
    wall_elapsed = time.perf_counter() - wall_start

    ids = [o.order_id for o in sink.orders]
    unique_ids = len(set(ids))
    missing = count - unique_ids

    return {
        "count": count,
        "gen_elapsed": gen_elapsed,
        "total_elapsed": wall_elapsed,
        "accepted": stats.accepted,
        "rejected": stats.rejected,
        "sim_rate": stats.accepted / wall_elapsed if wall_elapsed > 0 else 0,
        "missing": missing,
        "unique_ids": unique_ids, # ADDED THIS SO THE TEST DOESN'T FAIL
    }

async def run_all(scales, rate_per_sec, seed) -> None:
    print(f"=== ChronosMatch simulator benchmark ===")
    print(f"Target Rate: {rate_per_sec:,.0f}/s  Seed: {seed}")
    print()
    print(f"{'Count':>8} | {'Gen Time':>9} | {'Total Time':>10} | {'Accepted':>8} | {'Sim Rate/s':>10} | {'Missing':>7}")
    print("-" * 72)
    for scale in scales:
        res = await run_one(scale, rate_per_sec, seed)
        print(
            f"{res['count']:>8,} | {res['gen_elapsed']:>8.4f}s | "
            f"{res['total_elapsed']:>9.4f}s | {res['accepted']:>8,} | "
            f"{res['sim_rate']:>10,.0f} | {res['missing']:>7,}"
        )
    print("\nDone.")

def _parse_args():
    p = argparse.ArgumentParser(description="ChronosMatch benchmark")
    p.add_argument("--count", type=int, default=None)
    p.add_argument("--rate", type=float, default=1_000_000.0)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()

def main() -> None:
    args = _parse_args()
    scales = (args.count,) if args.count else DEFAULT_SCALES
    asyncio.run(run_all(scales, args.rate, args.seed))

if __name__ == "__main__":
    main()