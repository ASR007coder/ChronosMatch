
# ChronosMatch

Low-latency order matching engine and trading system simulator (educational).

## Setup

Needs Python 3.9+.

```bash
pip install -r requirements.txt
pytest -q
```

## Engine contract

See `docs/engine-interface.md`.

## Frontend Dashboard Progress

- Connected the frontend dashboard to the simulation backend API.
- Displayed simulation metrics and trade details.
- Improved the simulation loading message.
- Tested the simulation with 10 orders.
- Next task: Display trades in a structured table.

## Performance Benchmark Results

Tested the matching engine with different order sizes.

| Total Orders | Processed | Trades | Processing Time (ms) | Average Latency (ms) | Throughput (orders/sec) | Errors |
|---:|---:|---:|---:|---:|---:|---:|
| 100 | 100 | 50 | 0.202 | 0.002020 | 495049.48 | 0 |
| 1,000 | 1,000 | 500 | 0.860 | 0.000860 | 1162655.50 | 0 |
| 10,000 | 10,000 | 5,000 | 9.826 | 0.000983 | 1017718.48 | 0 |

### Key Observations

- All 11,100 orders were processed successfully across the three tests.
- A total of 5,550 trades were executed.
- No processing errors were reported.
- The 10,000-order test achieved approximately 1.02 million orders per second.

### Run Benchmark

Execute from the project root:

```bash
python benchmark.py
```

**Note:** Results represent a single benchmark run. Performance may vary between runs.
