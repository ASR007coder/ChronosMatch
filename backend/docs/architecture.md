# ChronosMatch — System Architecture

## 1. Project Overview

ChronosMatch is a market-matching system designed to process buy and sell orders, match compatible orders according to price-time priority, generate trade records, and collect performance metrics.

The system aims to use inter-process communication (IPC) through a shared-memory ring buffer to transfer orders efficiently between the market simulator and the matching engine. A binary message protocol will minimize serialization overhead, while monitoring and storage components will provide visibility into system activity and performance.

The project is organized into independent modules with clearly defined responsibilities so that team members can develop and test their components in parallel.

This document defines the target architecture, team responsibilities, communication principles, testing strategy, and development workflow.

## 2. Team Responsibilities

### 2.1 Asif — Team Lead, IPC Engineer, Backend and Dashboard Integration

**Primary ownership:** `ipc/`, system integration, backend, and frontend dashboard.

* Lead the project, coordinate milestones, assign responsibilities, and maintain the overall system architecture.
* Define and maintain interfaces shared between the simulator, IPC layer, matching engine, monitoring system, and storage layer.
* Design and implement the binary order-message protocol.
* Implement the shared-memory ring buffer using Python's `mmap` and `struct` modules.
* Implement IPC producer and consumer components for transferring orders between processes.
* Coordinate integration and resolve interface mismatches between team members' modules.
* Develop the FastAPI backend to expose market data, trade history, performance metrics, and system status through APIs.
* Develop the frontend dashboard to display market activity, completed trades, order-book information, performance metrics, and system health.
* Integrate the backend and dashboard with the matching engine, monitoring system, and storage layer through their agreed interfaces.
* Develop end-to-end integration tests and coordinate system-level performance benchmarks.
* Manage application startup, shutdown, error reporting, and final system integration.
* Review pull requests and merge changes into `main` only after the required checks pass.

### 2.2 Mahesh — Matching Engine Engineer

**Primary ownership:** `engine/`

* Maintain and improve the matching engine and order-book implementation.
* Implement matching according to price-time priority.
* Support partial fills and generate trade records when compatible orders match.
* Maintain the engine's public API and ensure compatibility with the agreed order interface.
* Validate matching behavior for edge cases, including invalid orders, partially filled orders, and orders that do not match.
* Write and maintain unit tests for matching rules and order-book behavior.
* Document the engine interface, matching rules, and trade-record format.
* Coordinate with Asif to integrate the engine with the IPC consumer.

### 2.3 Kavya — Market Simulator Engineer

**Primary ownership:** `pipeline/` or the agreed simulator module.

* Generate buy and sell orders with configurable prices, quantities, and order counts.
* Support configurable generation rates and reproducible workloads through random seeds.
* Implement different workload patterns for functional testing and performance benchmarking.
* Follow the agreed order schema and sequence-number rules.
* Submit generated orders through the agreed producer interface.
* Test order generation, input validation, and workload reproducibility.
* Evaluate producer backpressure and define how the simulator responds when the IPC buffer is full.
* Document workload configuration and simulator usage.

### 2.4 Vijay — Monitoring and Storage Engineer

**Primary ownership:** `monitoring/` and `storage/`

* Collect relevant order, trade, error, and system-performance metrics.
* Measure order-processing throughput and latency.
* Store completed trades and agreed system events in SQLite.
* Define interfaces for recording trades, querying stored data, and retrieving performance metrics.
* Implement storage validation and error handling.
* Write unit tests for metrics collection, database operations, and data retrieval.
* Provide the data required by the FastAPI backend and frontend dashboard.
* Coordinate with Asif to integrate monitoring and storage with the complete processing pipeline.

## 3. Target System Architecture and Data Flow

The intended order-processing pipeline is:

1. **Order generation:** Kavya's market simulator generates an order according to the configured workload.
2. **Order validation:** The IPC producer validates the order fields and checks that the order satisfies the agreed protocol requirements.
3. **Binary encoding:** The producer encodes the validated order into the agreed binary message format.
4. **Shared-memory transfer:** The producer writes the encoded message into the shared-memory ring buffer.
5. **Order consumption:** The IPC consumer reads the message from the ring buffer and decodes it into the agreed order representation.
6. **Order matching:** Mahesh's matching engine processes the order and updates the order book.
7. **Trade generation:** When compatible buy and sell orders match, the engine generates trade records.
8. **Monitoring and persistence:** Vijay's monitoring and storage components collect relevant metrics and persist completed trades and agreed events.
9. **Backend API:** The FastAPI backend exposes the required market data, trade history, metrics, and system status.
10. **Dashboard presentation:** The frontend dashboard retrieves data through the backend and presents market activity and system performance.

The intended architecture separates order transport, matching, monitoring, persistence, and presentation into distinct responsibilities.

**Important:** This is the target data flow. The complete pipeline must be implemented and verified through integration tests before it can be considered operational.

## 4. Main Modules and Directory Responsibilities

### 4.1 `pipeline/` — Market Simulation

Responsible for generating orders and defining market workloads.

Expected responsibilities include:

* Order generation and configuration.
* Workload patterns and random-seed management.
* Order-format compatibility.
* Submission of orders through the producer interface.

### 4.2 `ipc/` — Inter-Process Communication

Responsible for transferring orders between processes efficiently and safely.

Expected responsibilities include:

* Binary order encoding and decoding.
* Shared-memory ring-buffer implementation.
* Producer and consumer coordination.
* Buffer-capacity management.
* Handling full and empty buffer conditions.
* Protocol validation and communication errors.

### 4.3 `engine/` — Matching Engine

Responsible for order-book management and trade generation.

Expected responsibilities include:

* Maintaining buy and sell order books.
* Enforcing price-time priority.
* Processing incoming orders.
* Supporting partial fills.
* Generating trade records.
* Maintaining engine correctness through unit tests.

### 4.4 `monitoring/` — Metrics and Performance Monitoring

Responsible for collecting and reporting system metrics.

Expected responsibilities include:

* Order and trade counters.
* Error counters.
* Throughput measurements.
* Processing-latency measurements.
* Metrics interfaces for the backend and dashboard.

### 4.5 `storage/` — Persistent Data

Responsible for storing and retrieving completed trades and agreed system events.

Expected responsibilities include:

* SQLite database initialization and schema management.
* Trade persistence and retrieval.
* Relevant event storage.
* Database error handling.
* Storage tests.

### 4.6 `backend/` — API Layer

Responsible for exposing system data through FastAPI endpoints.

Expected responsibilities include:

* Market and order-book data endpoints.
* Trade-history endpoints.
* Metrics and performance endpoints.
* System-status endpoints.
* Input validation and API error responses.

The backend should consume the public interfaces provided by the engine, monitoring, and storage modules rather than duplicating their internal logic.

### 4.7 `frontend/` — Monitoring Dashboard

Responsible for presenting system information to users.

Expected responsibilities include:

* Displaying market activity and order-book information.
* Showing completed trades and trade history.
* Presenting throughput and latency metrics.
* Displaying system status and relevant errors.
* Retrieving data through the FastAPI backend.

### 4.8 `integration/` — System Integration and End-to-End Tests

Responsible for validating interactions between modules.

Expected responsibilities include:

* Testing the simulator-to-IPC flow.
* Testing IPC-to-engine communication.
* Verifying that matching produces the expected trades.
* Verifying trade persistence and metrics collection.
* Testing the complete order-to-trade workflow.
* Supporting end-to-end performance benchmarks.

The directory layout may evolve as implementation progresses. Public interfaces and ownership boundaries should remain explicit even when the physical file structure changes.

## 5. Communication and Interface Rules

All modules must follow the interfaces agreed upon by the team before dependent implementations are integrated.

### 5.1 Order Representation

* All components must use the agreed logical order schema.
* The IPC layer must use one documented binary message format.
* Binary field sizes, byte order, message types, and protocol version must be explicitly defined.
* Price values are represented as integers measured in paise.
* `BUY` is represented by `0`, and `SELL` is represented by `1`.
* Quantity must be a positive integer.
* Order identifiers and sequence numbers must follow the agreed field-size and validation rules.
* Sequence numbers must follow the matching engine's ordering contract.

### 5.2 IPC Contract

* The producer must validate orders before publishing them.
* The producer must not publish incomplete or incorrectly encoded messages.
* The consumer must validate messages before passing orders to the matching engine.
* Full and empty ring-buffer conditions must be handled safely.
* Producer and consumer synchronization must prevent readers from consuming incomplete messages.
* Unsupported protocol versions and message types must be rejected or reported according to the agreed protocol rules.

### 5.3 Module Ownership

* Each module must expose a clear public interface.
* A module must not duplicate another module's core responsibility.
* The matching engine owns matching logic and order-book state.
* The IPC layer owns message transport and binary encoding.
* The monitoring and storage modules own their respective metrics and persistence logic.
* The backend owns API exposure, while the frontend owns presentation.
* Changes to shared interfaces must be communicated to all affected team members.

**Note:** The final binary layout, sequence-number limits, and supported message types must be agreed upon and documented before protocol-dependent implementations are finalized.

## 6. Error Handling and Reliability

The system must define consistent behavior for expected failures and unexpected runtime conditions.

The following cases must be considered:

* Invalid order fields or unsupported values.
* Invalid binary messages.
* Unsupported protocol versions or message types.
* Binary encoding and decoding failures.
* A full shared-memory ring buffer.
* An empty shared-memory ring buffer.
* Producer or consumer synchronization failures.
* Matching-engine errors.
* Database and storage failures.
* Backend API errors.
* Unexpected process termination.
* Shutdown while messages remain unprocessed.

Errors should be reported clearly and handled without silently modifying order data.

Where appropriate, the system should use explicit return values, exceptions, counters, or structured logs. The exact recovery behavior—including retry policies, timeouts, and whether a failed message may be retried—must be specified in the relevant interface documents.

## 7. Testing Strategy

Testing must cover individual components as well as the complete processing pipeline.

### 7.1 Unit Tests

* Validate simulator behavior and order generation.
* Verify matching-engine correctness and edge cases.
* Test monitoring calculations.
* Test storage operations and database error handling.
* Test backend request validation and responses.

### 7.2 Protocol Tests

* Verify binary encoding and decoding.
* Confirm that encoded messages have the expected size.
* Validate field boundaries and supported values.
* Test invalid messages, unsupported versions, and malformed input.
* Verify that encoding followed by decoding preserves valid order data.

### 7.3 Ring-Buffer Tests

* Verify correct message publication and consumption.
* Test empty and full buffer conditions.
* Test buffer wraparound.
* Test producer-consumer synchronization.
* Verify that incomplete messages are never consumed.
* Test behavior under concurrent access where applicable.

### 7.4 Integration Tests

* Verify that simulator-generated orders reach the matching engine.
* Confirm that the engine produces the expected trades.
* Verify that trades and relevant events are recorded correctly.
* Confirm that monitoring metrics reflect actual processing.
* Test error propagation across module boundaries.

### 7.5 End-to-End and Performance Tests

* Execute the complete order-to-trade workflow.
* Measure throughput and processing latency under different workloads.
* Test behavior under high order-generation rates.
* Evaluate backpressure and buffer saturation.
* Check data consistency across the engine, monitoring system, storage, and API.
* Record benchmark configuration and results so that performance comparisons are reproducible.

The complete test suite must pass before the integrated system is considered ready for final evaluation.

## 8. Git and Development Workflow

The project uses Git branches to support parallel development and controlled integration.

1. Each team member develops changes on their assigned branch.
2. Team members keep their branches synchronized with the agreed project baseline.
3. Shared interfaces are discussed and documented before dependent modules are implemented.
4. Each member commits and pushes changes to their own branch.
5. Changes are submitted for review before being merged into `main`.
6. The team lead reviews the implementation, checks interface compatibility, and runs the relevant tests.
7. Integration conflicts and failing tests must be resolved before approval.
8. Approved changes are merged into `main`.
9. The integrated system is tested again after significant merges.

The `main` branch should contain reviewed, tested, and reasonably stable code rather than unfinished experimental work.

## 9. Implementation Status

This document describes the intended ChronosMatch architecture and the responsibilities assigned to the team.

The modules are being developed independently, and the target pipeline has not yet been verified as a complete integrated system.

The following items must be confirmed during implementation:

* The final binary order format and protocol contract.
* The producer and consumer interfaces.
* Shared-memory ring-buffer correctness and synchronization.
* Compatibility between the simulator and matching engine.
* Trade persistence and metrics integration.
* Backend and dashboard integration.
* End-to-end correctness and performance results.

A component should be considered integrated only after its interfaces have been connected and the relevant tests have passed.
