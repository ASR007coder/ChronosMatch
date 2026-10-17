# ChronosMatch Performance Metrics

## 1. Overview

ChronosMatch uses monitoring metrics to track order processing, trade execution, errors, throughput, and latency. These metrics help evaluate system behavior and identify performance issues.

## 2. Order Metrics

The `Metrics` class in `monitoring/metrics.py` tracks the following counters:

| Metric | Description |
|---|---|
| Orders generated | Total orders generated |
| Orders processed | Total orders processed by the application |
| Trades executed | Total trades executed |
| Errors | Total errors recorded |

## 3. Throughput

Throughput measures the number of processed orders per second.

**Formula:**

Throughput = Orders processed / Elapsed time in seconds

For example, processing 100 orders in 2 seconds gives a throughput of 50 orders per second.

Elapsed time must be greater than zero.

## 4. Latency

Latency measures the time taken for an operation. The statistics module accepts latency values in nanoseconds.

The latency summary reports:

- **Count:** Number of latency samples.
- **Median:** Middle latency value.
- **p95:** 95th-percentile latency.
- **p99:** 99th-percentile latency.
- **Maximum:** Largest recorded latency.

Lower latency generally indicates faster processing.

## 5. Percentile Calculation

The `percentile()` function sorts the input values and uses the nearest-rank method to select a percentile.

For 100 sorted values from 1 to 100:

- p95 = 95
- p99 = 99

The function rejects empty input and percentile values outside the range 0–100.

## 6. Testing

Automated tests are located in `monitoring/tests/test_statistics.py`.

Run the statistics tests:

```bash
python -m pytest monitoring/tests/test_statistics.py -v
```

Run the complete project test suite:

```bash
python -m pytest -q
```

The statistics tests cover throughput, invalid elapsed time, percentile calculations, invalid inputs, latency summaries, and empty latency samples.

## 7. Benchmarking Notes

Performance measurements should be collected from actual benchmark runs. Throughput and latency may vary with workload, hardware, and execution environment.

No benchmark performance claims are made in this document without measured results.