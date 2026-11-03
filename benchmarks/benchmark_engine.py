"""Compare Python and Cython matching-engine throughput."""

import argparse
import random
import time

from backend.engine.matching_engine import MatchingEngine
from backend.engine.cython.matching_core import CythonMatchingEngine


def generate_orders(count, seed=42):
    """Generate one deterministic workload for both engines."""
    rng = random.Random(seed)

    orders = []

    for sequence in range(1, count + 1):
        orders.append(
            (
                sequence,                  # order_id
                rng.choice((0, 1)),        # side: BUY or SELL
                rng.randint(9_900, 10_100),# price
                rng.randint(1, 10),        # quantity
                sequence,                  # sequence
            )
        )

    return orders


def run_benchmark(engine_cls, orders):
    """Run the workload and return elapsed time and final state."""
    engine = engine_cls()

    start = time.perf_counter()

    all_trades = []

    for order in orders:
        all_trades.extend(engine.submit(*order))

    elapsed = time.perf_counter() - start

    return {
        "elapsed": elapsed,
        "throughput": len(orders) / elapsed,
        "trades": all_trades,
        "depth": engine.depth(50),
        "best_bid": engine.best_bid(),
        "best_ask": engine.best_ask(),
        "orders_processed": engine.orders_processed,
        "trades_executed": engine.trades_executed,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark Python vs Cython matching engines."
    )
    parser.add_argument(
        "--orders",
        type=int,
        default=100_000,
        help="Number of orders to process (default: 100000)",
    )
    args = parser.parse_args()

    if args.orders <= 0:
        parser.error("--orders must be greater than zero")

    orders = generate_orders(args.orders)

    print(f"Benchmarking {args.orders:,} orders...")

    python_result = run_benchmark(MatchingEngine, orders)
    cython_result = run_benchmark(CythonMatchingEngine, orders)

    # Correctness check before comparing performance.
    assert python_result["trades"] == cython_result["trades"]
    assert python_result["depth"] == cython_result["depth"]
    assert python_result["best_bid"] == cython_result["best_bid"]
    assert python_result["best_ask"] == cython_result["best_ask"]
    assert (
        python_result["orders_processed"]
        == cython_result["orders_processed"]
    )
    assert (
        python_result["trades_executed"]
        == cython_result["trades_executed"]
    )

    speedup = (
        python_result["elapsed"] / cython_result["elapsed"]
        if cython_result["elapsed"] > 0
        else 0
    )

    print("\nChronosMatch Engine Benchmark")
    print("----------------------------")
    print(f"Orders:               {args.orders:,}")
    print(f"Python elapsed:       {python_result['elapsed']:.3f} seconds")
    print(f"Python throughput:    {python_result['throughput']:,.2f} orders/sec")
    print(f"Cython elapsed:       {cython_result['elapsed']:.3f} seconds")
    print(f"Cython throughput:    {cython_result['throughput']:,.2f} orders/sec")
    print(f"Cython speedup:       {speedup:.2f}x")
    print(f"Trades executed:      {python_result['trades_executed']:,}")
    print("Python/Cython parity: PASS")


if __name__ == "__main__":
    main()