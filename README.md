
# ChronosMatch

Low-latency order matching engine and trading system simulator (educational).

## Setup

Requires Python 3.9+.

```bash
pip install -r requirements.txt
```

## Run Tests

```bash
python -m pytest -q
```

## Engine Contract

See `docs/engine-interface.md`.

## Frontend Dashboard Progress

- Connected the frontend dashboard to the simulation backend API.
- Displayed simulation metrics and trade details.
- Improved the simulation loading message.
- Tested the simulation with different order sizes.
- Added performance metrics to the dashboard.
- Added a Reset Results feature.

## Performance Benchmark Results

The matching engine was tested with three different order sizes.

Each test was executed 5 times. The following table shows average processing time, average latency, and average throughput.

| Total Orders | Processed | Trades | Average Processing Time (ms) | Average Latency (ms) | Average Throughput (orders/sec) | Errors |
|---:|---:|---:|---:|---:|---:|---:|
| 100 | 100 | 50 | 0.088 | 0.000879 | 1,153,456.93 | 0 |
| 1,000 | 1,000 | 500 | 0.853 | 0.000853 | 1,172,974.88 | 0 |
| 10,000 | 10,000 | 5,000 | 9.463 | 0.000946 | 1,065,777.52 | 0 |

### Key Observations

- Each order-size test was repeated 5 times.
- All tested orders were processed successfully.
- Zero errors were reported across the benchmark runs.
- The 10,000-order test achieved approximately 1.07 million orders per second.
- Performance may vary depending on the system and execution environment.

## Run Benchmark

Execute from the project root:

```bash
python benchmark.py
```

## Latest Test Results

- Total tests passed: 76
- Failed tests: 0
- Test execution time: 0.23 seconds
