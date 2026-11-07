# Matching Engine Correctness Audit

**Owner:** Asif  
**Status:** Complete  
**Test command:** `python -m pytest backend/engine/tests -v`  
**Latest result:** 48 passed

## Documented Invariants

| Invariant | Implementation | Test Evidence | Status |
|---|---|---|---|
| Buy orders match eligible asks | `matching_engine.py` | `test_price_time_priority`, `test_sweeps_multiple_levels_best_price_first` | PASS |
| Sell orders match eligible bids | `matching_engine.py` | `test_aggressive_sell_hits_highest_bid_first` | PASS |
| Best price executes first | `matching_engine.py`, `order_book.py` | Sweep tests | PASS |
| FIFO within a price level | `order_book.py` deque + matching loop | `test_price_time_priority` | PASS |
| Trade executes at resting price | `matching_engine.py` | `test_brief_example_partial_fills` | PASS |
| No order is overfilled | `matching_engine.py` | `test_incoming_order_is_never_overfilled` | PASS |
| Remainder rests or is consumed | `matching_engine.py` | Partial-fill, remainder, and exact-fill tests | PASS |
| Sequence numbers strictly increase | `matching_engine.py` | Sequence rejection tests | PASS |
| Invalid side is rejected | `models.py` | Invalid-order tests | PASS |
| Non-positive price/quantity rejected | `models.py` | Invalid-order tests | PASS |
| Non-integer order values rejected | `models.py` | Non-integer validation tests | PASS |
| Rejected orders preserve state | `matching_engine.py` | Invalid-order state-preservation tests | PASS |
| Duplicate order IDs are not checked | Documented contract | Producer responsibility | PASS |
| Sequence gaps are not detected by engine | Documented contract | Pipeline responsibility | PASS |

## Findings

Integer-type validation was added to `validate_order()` so direct
`MatchingEngine.submit()` calls enforce the documented integer contract.

The engine test suite passes with 48 tests.