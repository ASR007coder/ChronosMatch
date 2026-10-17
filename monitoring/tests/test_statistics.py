
import pytest

from monitoring.statistics import (
    LatencyRecord,
    calculate_latency_summary,
    calculate_throughput,
    percentile,
)


def test_calculate_throughput():
    assert calculate_throughput(100, 2) == 50


def test_throughput_rejects_zero_elapsed_time():
    with pytest.raises(ValueError):
        calculate_throughput(100, 0)


def test_percentile_with_100_values():
    values = list(range(1, 101))

    assert percentile(values, 50) == 50
    assert percentile(values, 95) == 95
    assert percentile(values, 99) == 99


def test_percentile_rejects_empty_values():
    with pytest.raises(ValueError):
        percentile([], 95)


def test_percentile_rejects_invalid_percent():
    with pytest.raises(ValueError):
        percentile([10, 20, 30], 101)


def test_latency_summary():
    latencies = [
        LatencyRecord(100),
        LatencyRecord(200),
        LatencyRecord(300),
    ]

    result = calculate_latency_summary(latencies)

    assert result["count"] == 3
    assert result["median"] == 200
    assert result["p95"] == 300
    assert result["p99"] == 300
    assert result["max"] == 300


def test_empty_latency_summary():
    assert calculate_latency_summary([]) == {
        "count": 0,
        "median": 0,
        "p95": 0,
        "p99": 0,
        "max": 0,
    }
