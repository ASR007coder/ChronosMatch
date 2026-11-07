---

## 16. Final IPC Integration & Benchmarks (Week 2 Day 14)

### Producer API Integration
The simulator is now fully wired to Asif's real, synchronous IPC producer API. The `IPCProducerAdapter` calls the `submit()` function directly, passing the exact 6 fields and a `timeout` parameter to handle backpressure safely.

### Latest Performance Benchmarks
We ran the large-scale load test to prove the simulator handles high-frequency workloads without data loss.

| Orders Requested | Elapsed Time | Throughput (Orders/sec) | Rejected | Missing |
| :--- | :--- | :--- | :--- | :--- |
| **100,000** | **0.107s** | **931,675** | **0** | **0** |

### Dashboard Readiness
The `simulator/runner.py` module exposes a `get_dashboard_metrics()` function. This returns a JSON-ready dictionary with accepted, rejected, and elapsed time stats, which Vijay's dashboard will use to display live simulation results.