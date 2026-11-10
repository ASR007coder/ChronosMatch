
import time
import statistics

from engine.models import BUY, SELL, Order
from engine.matching_engine import MatchingEngine
from monitoring.statistics import calculate_throughput
from pipeline.runner import run_orders


def run_benchmark(total_orders):
    engine = MatchingEngine()
    orders = []

    # Generate orders
    for i in range(1, total_orders + 1):
        side = BUY if i % 2 != 0 else SELL

        orders.append(
            Order(
                order_id=i,
                sequence=i,
                side=side,
                price=50000,
                quantity=1
            )
        )

    # Measure processing time
    start_time = time.perf_counter()

    metrics, trades = run_orders(orders, engine=engine)

    end_time = time.perf_counter()

    elapsed = end_time - start_time
    elapsed_ms = elapsed * 1000

    throughput = calculate_throughput(
        metrics.orders_processed,
        elapsed
    )

    average_latency = (
        elapsed_ms / metrics.orders_processed
        if metrics.orders_processed > 0 else 0
    )

    return {
        "orders": total_orders,
        "processed": metrics.orders_processed,
        "trades": metrics.trades_executed,
        "processing_time_ms": elapsed_ms,
        "average_latency_ms": average_latency,
        "throughput": throughput,
        "errors": metrics.errors
    }


def main():
    test_sizes = [100, 1000, 10000]
    runs = 5

    print("\nCHRONOSMATCH PERFORMANCE BENCHMARK")
    print(f"Number of runs per test: {runs}")
    print("=" * 85)

    print(
        f"{'Orders':<12}"
        f"{'Processed':<12}"
        f"{'Trades':<10}"
        f"{'Avg Time (ms)':<17}"
        f"{'Avg Latency (ms)':<19}"
        f"{'Avg Throughput/sec':<20}"
        f"{'Errors':<8}"
    )

    print("-" * 101)

    for size in test_sizes:
        results = []

        # Run benchmark five times
        for _ in range(runs):
            result = run_benchmark(size)
            results.append(result)

        avg_time = statistics.mean(
            r["processing_time_ms"] for r in results
        )

        avg_latency = statistics.mean(
            r["average_latency_ms"] for r in results
        )

        avg_throughput = statistics.mean(
            r["throughput"] for r in results
        )

        # Verify that all runs processed the expected orders
        total_errors = sum(r["errors"] for r in results)

        print(
            f"{size:<12}"
            f"{results[-1]['processed']:<12}"
            f"{results[-1]['trades']:<10}"
            f"{avg_time:<17.3f}"
            f"{avg_latency:<19.6f}"
            f"{avg_throughput:<20.2f}"
            f"{total_errors:<8}"
        )

    print("=" * 101)


if __name__ == "__main__":
    main()
