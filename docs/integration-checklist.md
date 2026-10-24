# Week 2 Integration Checklist

## Kavya (Simulator) - ✅ Complete
- [x] Order Generator & Workloads (Week 1)
- [x] IPC Producer Adapter wired to Asif's synchronous API
- [x] FastAPI Lifecycle Runner (`runner.py`)
- [x] 86+ tests passing (0% data loss)
- [x] Benchmarked at 100K orders (931K/sec)

## Waiting On (Blockers)
- [ ] **Asif:** Review and merge PR #2
- [ ] **Asif:** Connect `runner.py` to FastAPI backend
- [ ] **Vijay:** Connect dashboard UI to display live metrics

## Next Step for Kavya
Once Asif merges PR #2 and connects the backend, I will run the live end-to-end test to ensure the dashboard displays accurate throughput and latency.