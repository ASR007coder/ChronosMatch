
# ChronosMatch Architecture

## Overview
ChronosMatch is a simulated trading system that processes buy and sell orders.

## System Flow

```text
Order Generator
      |
      v
Binary Encoder
      |
      v
Shared Ring Buffer
      |
      v
Matching Engine
      |
      v
Trade Ledger
      |
      v
Monitoring Dashboard
```

## Components
1. **Order Generator:** Creates orders and assigns increasing sequence numbers starting at 1.
2. **Binary Encoder:** Converts orders into the agreed binary format.
3. **Shared Ring Buffer:** Transfers orders between producer and consumer.
4. **Matching Engine:** Matches buy and sell orders using price-time priority.
5. **Trade Ledger:** Records completed trades.
6. **Monitoring Dashboard:** Displays order counts, trades, latency, and throughput.

## Metrics to Monitor
- Orders generated
- Orders processed
- Trades completed
- Errors
- Processing latency
- Throughput (orders per second)

## Important Rules
- Import BUY and SELL from engine/models.py.
- Prices are integers in paise, never floats.
- The generator assigns sequence numbers.
- Trades execute at the resting order's price.
- Follow docs/engine-interface.md.
