# ChronosMatch – Zero-Copy High-Frequency Trading Engine

**Domain:** FinTech & Low-Latency Systems  
**Programming Language:** Python  
**Project Duration:** 1 Month

---

## 1. Project Overview

ChronosMatch is a low-latency order matching engine designed for High-Frequency Trading (HFT).

The project aims to reduce unnecessary data copying, minimize serialization overhead, and improve order-processing performance through optimized processing and Zero-Copy architecture.

The system is designed to process Buy and Sell orders efficiently while monitoring trading activity and performance through a dashboard.

## 2. Problem Statement

Traditional trading systems may experience performance delays due to data copying, serialization, and processing overhead.

ChronosMatch aims to address these challenges by exploring Zero-Copy data transfer, efficient order matching, and performance monitoring techniques.

## 3. Project Objectives

- Develop a low-latency order matching system.
- Process Buy and Sell orders efficiently.
- Reduce unnecessary data copying between processes.
- Minimize serialization overhead.
- Monitor processing time, latency, and throughput.
- Display trading results and performance metrics through a dashboard.

## 4. Technologies Used

| Technology | Purpose |
|---|---|
| Python | Core application development |
| FastAPI | Backend API |
| HTML, CSS, JavaScript | Frontend dashboard |
| Pytest | Automated testing |
| Git and GitHub | Version control |
| Benchmarking | Performance measurement |

## 5. Project Architecture

**Current application workflow:**

Order Generator → Order Processing → Matching Engine → Trade Results → Monitoring Dashboard

**Planned Zero-Copy architecture:**

Python Order Generator → Memory-Mapped Ring Buffer → Matching Engine → Trade Ledger → Monitoring Dashboard

The planned architecture uses shared memory and a ring buffer to reduce unnecessary data copying between processes.

## 6. Week-Wise Project Progress

### Week 1 – Project Understanding and Initial Development

- Reviewed project requirements and system architecture.
- Studied the Buy and Sell order-matching workflow.
- Explored the Python backend and matching-engine functionality.
- Reviewed the frontend dashboard structure.
- Performed initial validation of order-processing functionality.
- Identified important performance metrics, including processing time, latency, throughput, and errors.

### Week 2 – Dashboard Integration and Performance Monitoring

- Connected the frontend dashboard with the simulation backend API.
- Integrated simulation metrics and trade details into the dashboard.
- Improved the simulation loading message.
- Implemented the Reset Results feature.
- Tested the simulation with 100, 1,000, and 10,000 orders.
- Enhanced the benchmark script to execute five runs for each order size.
- Calculated average processing time, latency, and throughput.
- Analyzed benchmark results.
- Updated performance documentation in GitHub README.
- Executed automated tests using Pytest.

## 7. Individual Contributions – Monitoring and Integration

During the first two weeks, my contributions focused on performance monitoring, benchmarking, integration verification, testing, and documentation.

### Key Contributions

1. **Performance Benchmarking:** Updated the benchmark script to execute five iterations for each workload.
2. **Latency Analysis:** Calculated and analyzed average processing latency.
3. **Throughput Analysis:** Measured the number of orders processed per second.
4. **Integration Verification:** Verified frontend-backend communication and dashboard metrics.
5. **Functional Testing:** Checked simulation results, trade details, and Reset Results functionality.
6. **Automated Testing:** Executed the project test suite using Pytest.
7. **Documentation:** Updated benchmark results and technical progress in GitHub README.

## 8. Performance Benchmark Results

Each order size was tested five times.

| Total Orders | Processed Orders | Trades Executed | Avg. Processing Time | Avg. Latency | Avg. Throughput |
|---:|---:|---:|---:|---:|---:|
| 100 | 100 | 50 | 0.088 ms | 0.000879 ms | 1,153,456.93 orders/sec |
| 1,000 | 1,000 | 500 | 0.853 ms | 0.000853 ms | 1,172,974.88 orders/sec |
| 10,000 | 10,000 | 5,000 | 9.463 ms | 0.000946 ms | 1,065,777.52 orders/sec |

### Key Observations

- All tested orders were processed successfully.
- Zero errors were reported.
- The 10,000-order test achieved approximately 1.07 million orders per second.
- Performance results may vary depending on the execution environment.

## 9. Testing Results

| Testing Details | Result |
|---|---:|
| Total Tests Passed | 76 |
| Failed Tests | 0 |
| Execution Time | 0.23 seconds |

**Testing Framework:** Pytest

## 10. Pending Work and Future Improvements

- Implement the memory-mapped shared ring buffer using `mmap`.
- Integrate Zero-Copy Inter-Process Communication (IPC).
- Develop and integrate the Cython matching engine.
- Optimize order-processing performance.
- Measure end-to-end latency using `time.perf_counter_ns()`.
- Improve the monitoring dashboard.
- Integrate trade storage with SQLite or ClickHouse.

## 11. Conclusion

During the first two weeks, the project focused on understanding the system architecture, order processing, dashboard integration, performance benchmarking, and automated testing.

The monitoring and integration contributions helped evaluate application functionality and establish an initial performance baseline.

The upcoming development phase will focus on shared-memory communication, Zero-Copy IPC integration, Cython optimization, and further performance evaluation.