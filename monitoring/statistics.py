
from dataclasses import dataclass
from statistics import median


@dataclass
class LatencyRecord:
    latency_ns: int


def calculate_throughput(orders_processed, elapsed_seconds):
    if elapsed_seconds <= 0:
        raise ValueError("Elapsed time must be positive")

    if orders_processed < 0:
        raise ValueError("Orders processed cannot be negative")

    return orders_processed / elapsed_seconds


def percentile(values, percent):
    if not 0 <= percent <= 100:
        raise ValueError("Percentile must be between 0 and 100")

    if not values:
        raise ValueError("Values cannot be empty")

    if any(value < 0 for value in values):
        raise ValueError("Values cannot be negative")

    sorted_values = sorted(values)
    rank = max(1, int((percent / 100) * len(sorted_values) + 0.999999))

    return sorted_values[rank - 1]


def calculate_latency_summary(latencies):
    if not latencies:
        return {
            "count": 0,
            "median": 0,
            "p95": 0,
            "p99": 0,
            "max": 0,
        }

    values = [item.latency_ns if isinstance(item, LatencyRecord) else item
              for item in latencies]

    return {
        "count": len(values),
        "median": median(values),
        "p95": percentile(values, 95),
        "p99": percentile(values, 99),
        "max": max(values),
    }
