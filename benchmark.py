
import time

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

    print("\nCHRONOSMATCH PERFORMANCE BENCHMARK")
    print("=" * 85)

    print(
        f"{'Orders':<12}"
        f"{'Processed':<12}"
        f"{'Trades':<10}"
        f"{'Time (ms)':<15}"
        f"{'Latency (ms)':<15}"
        f"{'Throughput/sec':<18}"
        f"{'Errors':<8}"
    )

    print("-" * 85)

    for size in test_sizes:
        result = run_benchmark(size)

        print(
            f"{result['orders']:<12}"
            f"{result['processed']:<12}"
            f"{result['trades']:<10}"
            f"{result['processing_time_ms']:<15.3f}"
            f"{result['average_latency_ms']:<15.6f}"
            f"{result['throughput']:<18.2f}"
            f"{result['errors']:<8}"
        )

    print("=" * 85)


if __name__ == "__main__":
    main()
