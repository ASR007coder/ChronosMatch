# Simulator Design — ChronosMatch

**Owner:** Member 2 (Order Pipeline / Market Simulator)
**Status:** Week 1 complete
**Tests:** 48/48 passing

---

## 1. Purpose

The simulator generates a reproducible stream of valid buy/sell
orders and submits them to a sink. In Week 1, the sink is in-memory.
In Week 2, Asif's IPC producer will implement the same `OrderSink`
interface.

The simulator is the first stage in the pipeline:

    Simulator -> IPC producer -> Ring buffer -> Matching engine -> Metrics

---

## 2. Module layout

    simulator/
    ├── __init__.py            package marker
    ├── config.py              SimulatorConfig dataclass
    ├── order_format.py        64-byte binary encode/decode
    ├── order_generator.py     deterministic, seeded generator
    ├── workload.py            4 workload kinds
    ├── market_simulator.py    async producer loop + sinks + stats
    └── benchmark.py           load-test script

Tests live in `tests/simulator/` per team convention.

---

## 3. Order model

Every order is a `@dataclass(slots=True)` with:

| Field        | Type | Meaning                          |
|--------------|------|----------------------------------|
| order_id     | int  | unique, starts at 1              |
| sequence     | int  | monotonic, starts at 1           |
| price        | int  | integer paise (never float)      |
| timestamp_ns | int  | nanoseconds since epoch          |
| quantity     | int  | units, > 0                       |
| side         | int  | BUY=0 or SELL=1 (from engine)    |

BUY and SELL are imported from `engine.models`. They are never
redefined locally in production code.

---

## 4. Binary format

Fixed 64-byte record, little-endian, format `"<QQqQIB27x"`:

| Offset | Size | Format | Field        |
|-------:|-----:|:------:|:-------------|
| 0      | 8    | Q      | order_id     |
| 8      | 8    | Q      | sequence     |
| 16     | 8    | q      | price        |
| 24     | 8    | Q      | timestamp_ns |
| 32     | 4    | I      | quantity     |
| 36     | 1    | B      | side         |
| 37     | 27   | 27x    | padding      |

Validation in `encode()`:
- order_id >= 0
- sequence >= 1
- price > 0
- quantity > 0
- side in {BUY, SELL}

`decode()` raises `ValueError` if record length != 64.

---

## 5. Order generator

`OrderGenerator(config)` uses a seeded `random.Random`, so two runs
with the same seed produce IDENTICAL order streams.

Rules:
- IDs start at 1, increment by 1
- Sequences start at 1, increment by 1
- Timestamps monotonic (fixed 1 ms step)
- Reset reproduces initial state
- Never uses global `random`

---

## 6. Workloads

`WorkloadConfig(kind, count, seed, ...)` — 4 kinds:

| Kind           | Behavior                                             |
|----------------|------------------------------------------------------|
| MIXED          | random buys and sells across the price band          |
| MARKETABLE     | BUYs > reference, SELLs < reference (cross the book) |
| NON_MARKETABLE | BUYs < reference, SELLs > reference (build depth)    |
| BURST          | timestamp compression simulates a rate spike         |

All workloads are deterministic given the seed.

---

## 7. Async market simulator

`MarketSimulator(config, sink)` — async producer loop.

Flow:
1. Pre-generate the workload
2. For each order: submit to sink, sleep to respect target rate
3. Handle rejections with bounded retries
4. Collect statistics

**Rate control:** uses scheduled-time sleeping (works around
Windows asyncio ~15 ms granularity — up to 1M orders/s).

Sink interface:

    class OrderSink(Protocol):
        async def submit(self, order) -> bool: ...

The simulator never implements its own IPC or shared-memory sync.

---

## 8. Sinks

| Sink          | Purpose                                          |
|---------------|--------------------------------------------------|
| InMemorySink  | Week 1 default; stores accepted orders in a list |
| RejectingSink | Test helper; rejects every Nth order             |

---

## 9. Statistics

`SimulatorStats` tracks:
- generated, submitted, accepted, rejected, retried
- elapsed_seconds
- accepted_rate

---

## 10. Benchmark results

Single-process, in-memory sink, Windows, Python 3.12:

| Orders   | Elapsed  | Rate        |
|---------:|---------:|------------:|
| 1,000    | 0.001 s  | 819,135 /s  |
| 10,000   | 0.021 s  | 469,109 /s  |
| 100,000  | 0.103 s  | 969,284 /s  |

Zero orders lost, zero duplicates at every scale.

Note: these rates reflect the in-memory sink, not the real IPC + engine.

---

## 11. Tests

`tests/simulator/`:

- test_order_generator.py     13 tests
- test_workload.py            16 tests
- test_market_simulator.py     8 tests
- test_rate_control.py         7 tests
- test_load.py                 4 tests

Total: 48 tests passing.

---

## 12. Limitations and next steps

- In-memory sink only (Week 1)
- Real IPC producer integration is Week 2 work
- True end-to-end throughput requires IPC + engine
- 1M order test is a benchmark, not a unit test

---

## 13. Boundaries

- **Asif (IPC):** owns ring buffer + producer API. Simulator uses
  `OrderSink`; IPC producer will implement it.
- **Mahesh (engine):** owns `engine.models`. Simulator imports
  BUY/SELL from there.
- **Vijay (metrics):** consumes simulator stats.




## 17. Week 3: Simulator Deep Improvement (Audit & Stabilize)

As per the Week 3 roadmap, we are beginning the deep improvement phase.

### Day 1 Audit Findings:
- [x] Verified order_format.py strictly follows the 64-byte binary protocol.
- [x] Verified order_generator.py produces deterministic output with the same seed.
- [ ] TODO: Enhance workload validation bounds (Day 2).
- [ ] TODO: Verify IPC retry logic does not cause duplicate orders (Day 3).

Status: **Audit Complete**.



## 19. Week 4: Final Integration Support

- Simulator is fully merged and ready for FastAPI integration.
- Runner class (`SimulatorRun`) exposes lifecycle control (`start`, `stop`) and JSON-ready metrics (`snapshot`).
- Assisting Asif and Vijay with final dashboard integration and testing.

## 20. Week 4 Final Submission

- All simulator code is finalized and merged.
- FastAPI runner (`SimulatorRun`) is ready for the final demonstration.
- Week 3 deep improvements (stress testing, timeouts, E2E pipeline) are complete.