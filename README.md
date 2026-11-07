# ChronosMatch
### Low-Latency Market Matching Engine

---

## 1. Introduction

ChronosMatch is a low-latency market matching engine project designed to simulate financial market order flow, process buy and sell orders, execute matching operations, and measure system performance.

The primary objective of the project is to develop and evaluate an efficient order-processing pipeline capable of handling a large volume of market orders while maintaining low matching-engine latency and reliable order execution.

The system simulates market activity by generating buy and sell orders, transferring them through an Inter-Process Communication (IPC) pipeline, and processing them through a matching engine.

ChronosMatch focuses on three major engineering objectives:

- **Performance:** Achieve high order-processing throughput with low matching latency.
- **Reliability:** Ensure that orders are transferred and processed without loss or duplication.
- **Observability:** Measure throughput, latency, execution counts, and pipeline-stage timings.

The project also includes a web-based dashboard that allows users to configure simulation workloads and inspect benchmark results.

### Project Objectives

1. Generate large volumes of deterministic market orders.
2. Implement an efficient order-processing and matching pipeline.
3. Transfer orders using a high-performance IPC mechanism.
4. Integrate the matching engine with the IPC consumer.
5. Measure matching latency and overall throughput.
6. Verify order integrity throughout the pipeline.
7. Provide a dashboard for simulation control and performance analysis.

---

## 2. System Architecture

ChronosMatch follows a modular architecture in which workload generation, order transport, matching, monitoring, and visualization are separated into individual components.

### High-Level Architecture

                  CHRONOSMATCH
                        |
                        v
              MARKET SIMULATOR
                        |
                        v
               ORDER GENERATION
                        |
                        v
                IPC PRODUCER
                        |
                        v
              BATCH IPC ADAPTER
                        |
                        v
                  FAST RING
                        |
                        v
                IPC CONSUMER
                        |
                        v
               MATCHING ENGINE
                        |
                        v
                TRADE EXECUTION
                        |
              +---------+---------+
              |                   |
              v                   v
         MONITORING           ORDER BOOK
              |                   |
              +---------+---------+
                        |
                        v
                 RESULT METRICS
                        |
                        v
                 FASTAPI BACKEND
                        |
                        v
                WEB DASHBOARD


### 2.1 Market Simulator

The market simulator generates market orders according to a configurable workload.

Each order contains information such as:

- Order ID
- Sequence number
- Price
- Timestamp
- Quantity
- Side (BUY or SELL)

The simulator supports configurable order counts and workload parameters.

Its responsibility is to generate and submit orders to the IPC producer.

### 2.2 IPC Producer

The producer is responsible for transferring generated orders into the IPC pipeline.

It validates and encodes order information before submitting it to the underlying transport mechanism.

The project also uses a batch producer adapter to reduce the coordination overhead associated with submitting individual orders.

### 2.3 FastRing IPC

FastRing is the shared-memory-based communication component used to transfer order data between the producer and consumer.

It provides a bounded communication buffer through which orders are published and consumed.

The pipeline processes orders in batches to reduce per-order communication overhead.

### 2.4 IPC Consumer

The consumer reads published order records from FastRing.

Its responsibilities include:

- Reading batches of order records.
- Unpacking binary order data.
- Validating order records.
- Forwarding orders to the matching engine.
- Collecting processing and latency statistics.

### 2.5 Matching Engine

The matching engine processes incoming buy and sell orders according to their price and sequence information.

Its responsibilities include:

- Processing incoming orders.
- Matching compatible buy and sell orders.
- Executing trades.
- Maintaining order-book state.
- Tracking processed orders and executed trades.

The IPC pipeline integrates with the Cython-based matching engine implementation.

### 2.6 Monitoring and Storage

The monitoring layer tracks system activity and performance.

Important measurements include:

- Generated orders
- Accepted orders
- Published orders
- Received orders
- Processed orders
- Executed trades
- Processing latency
- Throughput
- Pipeline-stage execution time

These measurements help evaluate system performance and identify potential bottlenecks.

### 2.7 Backend API

The backend is implemented using FastAPI.

It provides endpoints for:

- Checking application health.
- Starting a simulation.
- Retrieving the latest simulation status.
- Retrieving benchmark results.

The backend executes the benchmark as a background task and exposes its results to the frontend.

### 2.8 Frontend Dashboard

The frontend provides a web-based interface for controlling and monitoring simulations.

It includes:

- Simulation configuration.
- Order-count selection.
- Simulation execution controls.
- Throughput and latency metrics.
- Pipeline-stage timings.
- Execution-integrity information.
- Market activity visualization.

The current buy/sell market visualization is illustrative frontend animation. Its events are not actual matching-engine events or live order-book updates.

---

## 3. Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core application and pipeline implementation |
| Cython | Matching-engine implementation |
| FastAPI | Backend API |
| asyncio | Asynchronous simulation orchestration |
| threading | Producer-consumer coordination |
| Shared Memory | IPC communication |
| Binary Serialization | Compact order representation |
| SQLite | Storage component, where configured |
| HTML | Dashboard structure |
| CSS | Dashboard styling |
| JavaScript | Frontend interaction and visualization |
| pytest | Automated testing |

---

## 4. Team Members and Responsibilities

###  4.1 Kavya — Market Simulator and Order Generation

Kavya is responsible for the market simulation and order-generation component.

Her work focuses on generating structured market orders, integrating with the IPC layer, and providing the FastAPI lifecycle management for the pipeline.

**Major responsibilities:**

- Designing the 64-byte binary market order format with validation.
- Implementing the deterministic order-generation components.
- Generating 4 deterministic market workloads (mixed, marketable, non-marketable, burst).
- Building the IPC Producer Adapter with timeout and backpressure handling.
- Building the FastAPI Lifecycle Manager (`runner.py`).
- Writing 85+ unit, stress, and end-to-end integration tests.
- Achieving 931,000 orders/sec in benchmarks without data loss.

**Key project components:**

- `simulator/order_format.py`
- `simulator/order_generator.py`
- `simulator/workload.py`
- `simulator/market_simulator.py`
- `simulator/producer_adapter.py`
- `simulator/runner.py`
- `tests/simulator/` and `tests/integration/`

**Contribution to ChronosMatch:**

Kavya's work provides the input workload for the complete system. Her simulator generates reproducible orders, handles IPC timeouts safely, and exposes JSON metrics via FastAPI, ensuring the pipeline can be tested reliably end-to-end.

---

### 4.2 Vijay — Monitoring and Metrics

Vijay is responsible for the monitoring and metrics component of the project.

His work focuses on tracking order-processing activity and collecting execution-related statistics.

**Major responsibilities:**

- Designing monitoring metrics.
- Tracking generated and processed orders.
- Tracking executed trades.
- Monitoring errors during processing.
- Supporting execution statistics.
- Contributing to the monitoring and storage responsibilities.

**Key project components:**

- `monitoring/metrics.py`
- Monitoring-related tests and supporting components.

**Contribution to ChronosMatch:**

Vijay's work provides visibility into the system's execution behavior.

Monitoring metrics help determine whether orders are processed correctly and provide information needed to evaluate system performance and reliability.

---

### 4.3 Asif — IPC Integration, Backend and System Integration

Asif is responsible for IPC integration and the overall integration of the simulation pipeline.

His work focuses on connecting the market simulator, IPC communication mechanism, matching engine, benchmark execution, and dashboard.

**Major responsibilities:**

**A. IPC Architecture and Integration**

- Integrating the producer and consumer components.
- Implementing and integrating the batch IPC producer adapter.
- Integrating FastRing into the processing pipeline.
- Coordinating producer-consumer communication.
- Integrating the IPC consumer with the matching engine.
- Maintaining reliable order transfer across pipeline stages.

**B. Simulation Pipeline**

- Integrating the market simulator with the IPC pipeline.
- Implementing the asynchronous simulation pipeline.
- Coordinating consumer-thread execution.
- Processing orders in batches.
- Collecting per-order matching-engine latency.
- Collecting pipeline-stage timings.
- Implementing order-ID integrity verification.
- Verifying that generated, accepted, published, received, and processed order counts remain consistent.

**C. Benchmarking and Performance Analysis**

- Implementing and running benchmark workloads.
- Evaluating throughput and latency.
- Comparing performance across different workload sizes.
- Identifying performance bottlenecks.
- Analyzing producer queue wait, consumer processing, matching, and trade materialization costs.

**D. Backend Development**

- Developing the FastAPI application.
- Integrating health, simulation, and dashboard routers.
- Implementing simulation execution as a background task.
- Exposing simulation status and benchmark metrics through API endpoints.
- Connecting benchmark results to the frontend.

**E. Frontend Dashboard**

- Developing the simulation dashboard.
- Implementing simulation configuration and execution controls.
- Displaying throughput and latency metrics.
- Displaying pipeline-stage timings.
- Displaying execution-integrity results.
- Adding an illustrative buy/sell market visualization.

**Key project components:**

- `backend/ipc/`
- `backend/pipeline/ipc_pipeline.py`
- `backend/simulator/batch_adapter.py`
- `backend/simulator/market_simulator.py`
- `backend/simulator/ipc_benchmark.py`
- `backend/app/`
- `frontend/index.html`
- `frontend/style.css`
- `frontend/script.js`

**Contribution to ChronosMatch:**

Asif's work connects the individual project components into an integrated, measurable system.

The IPC pipeline enables generated orders to travel through the communication layer and reach the matching engine. The benchmark and monitoring integration then make it possible to evaluate the complete processing workflow.

---

## 5. Order Processing Workflow

The main execution flow follows these steps:

1. The user selects the desired number of orders from the dashboard.
2. The frontend sends a simulation request to the FastAPI backend.
3. The backend starts the benchmark as a background task.
4. The market simulator generates the configured workload.
5. The producer adapter submits orders to FastRing.
6. The consumer reads batches of order records.
7. The consumer validates and unpacks the records.
8. The Cython matching engine processes each order.
9. The engine executes trades when compatible orders are available.
10. The pipeline collects execution statistics and latency measurements.
11. Integrity checks verify that the expected orders were processed.
12. The backend exposes the completed benchmark results.
13. The frontend displays the final performance metrics.

---

## 6. Performance Measurement

ChronosMatch evaluates performance using several important metrics.

| Metric | Description |
|---|---|
| Orders Processed | Total orders handled by the matching engine |
| Trades Executed | Total trades successfully executed |
| Mean Latency | Average matching-engine submission latency |
| P50 Latency | Median matching-engine submission latency |
| P95 Latency | 95th-percentile submission latency |
| P99 Latency | 99th-percentile submission latency |
| Maximum Latency | Highest recorded submission latency |
| Steady-State Throughput | Processed orders divided by steady-state execution time |
| Wall Throughput | Processed orders divided by total pipeline wall time |

### Pipeline Timing Measurements

The system also measures the time spent in individual pipeline stages:

- Workload construction
- Simulator execution
- Producer queue waiting
- Producer publishing
- Consumer receiving
- Consumer timeout
- Matching-engine processing
- Trade materialization
- Order-book depth calculation
- Adapter draining
- Consumer thread joining
- Shared-memory cleanup

These measurements help identify where optimization efforts should be concentrated.

---

## 7. Benchmark Results

The following are representative benchmark results from the current implementation.

### 1 Million Orders

| Metric | Result |
|---|---:|
| Orders Processed | 1,000,000 |
| Trades Executed | 775,118 |
| Wall Throughput | 213,338 orders/sec |
| Steady-State Throughput | 458,158 orders/sec |
| Mean Latency | 0.96 µs |
| P50 Latency | 0.80 µs |
| P95 Latency | 1.30 µs |
| P99 Latency | 2.10 µs |

**Benchmark observations:**

- The pipeline successfully processed both workloads.
- Order-processing integrity checks passed.
- Matching-engine submission latency remained in the low-microsecond range.
- Throughput decreased when scaling from one million to ten million orders.
- Producer queue waiting and trade materialization are areas worth investigating for future optimization.

These measurements are environment-dependent and should not be treated as guaranteed performance figures.

---

## 8. Running the Project

### Prerequisites

- Python 3.10 or a compatible project-supported version.
- A working virtual environment.
- Required Python dependencies.
- Cython matching-engine extension built successfully.

### Step 1: Clone the Repository

```bash
git clone <REPOSITORY_URL>
cd ChronosMatch
```

### Step 2: Create a Virtual Environment

Windows PowerShell:

```powershell
python -m venv backend/.venv
```

Activate it:

```powershell
backend/.venv/Scripts/Activate.ps1
```

### Step 3: Install Dependencies

If the repository contains a requirements file:

```powershell
pip install -r requirements.txt
```

Ensure that the Cython extension has been built according to the project's build configuration.

### Step 4: Start the Backend

From the project root:

```powershell
python -m uvicorn backend.app.run:app --reload
```

### Step 5: Open the Dashboard

Visit:

```text
http://127.0.0.1:8000
```

### Step 6: Run a Simulation

1. Enter the desired order count.
2. Click **START SIMULATION**.
3. Wait for the benchmark to complete.
4. Review throughput, latency, pipeline timings, and integrity metrics.

The dashboard currently supports order counts between 10,000 and 10,000,000.

### Step 7: Run the CLI Benchmark

Example:

```powershell
python -m backend.simulator.ipc_benchmark --count 1000000
```

---

## 9. Project Reliability and Integrity

Correctness is as important as performance in a market matching system.

ChronosMatch includes checks to verify that orders are not silently lost or duplicated during processing.

Important checks include:

- Generated workload IDs are unique.
- Accepted orders match published orders.
- Published orders match received orders.
- Received orders match processed orders.
- Duplicate order IDs are detected.
- Missing order IDs are detected.
- Unexpected order IDs are detected.
- Latency sample counts match processed order counts.

These checks help establish confidence in benchmark results.

---

## 10. Current Development Status

The project currently includes:

- Market workload generation.
- IPC producer-consumer integration.
- Batch-based order publishing and receiving.
- FastRing communication.
- Cython matching-engine integration.
- Trade execution and order-book depth reporting.
- Latency and throughput measurement.
- Order-ID integrity verification.
- FastAPI simulation and dashboard endpoints.
- Frontend simulation controls and performance dashboard.
- Illustrative buy/sell market animation.

### Future Development

Potential areas for further development include:

1. Improving throughput at larger workload sizes.
2. Reducing producer-consumer coordination overhead.
3. Optimizing trade materialization.
4. Improving memory efficiency for large workloads.
5. Adding real-time telemetry from the matching engine.
6. Connecting actual order-book changes to the frontend.
7. Adding richer benchmark comparisons and historical performance tracking.
8. Expanding automated integration and stress testing.

---

## 11. Conclusion

ChronosMatch is an engineering project focused on building and evaluating a modular, high-performance market matching pipeline.

The project brings together market simulation, IPC communication, matching-engine integration, performance monitoring, benchmarking, and a web-based dashboard.

By separating these responsibilities into individual components, ChronosMatch provides a foundation for experimenting with low-latency order processing, measuring performance under different workloads, and identifying opportunities for further optimization.

The central objective is not simply to process a large number of orders, but to process them efficiently, reliably, and with measurable performance.

---

**Project:** ChronosMatch  
**Category:** Low-Latency Market Matching Engine  
**Backend:** Python, FastAPI, Cython  
**Frontend:** HTML, CSS, JavaScript  
**Communication:** Shared-Memory IPC  
**Primary Focus:** Performance, Reliability, and Order Processing
