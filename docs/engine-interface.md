# Matching Engine Interface (owner: Asif)

Kept in its own file so it doesn't conflict with `docs/architecture.md` (Vijay). Link to it from there.

## Order (engine/models.py)
| Field | Type | Meaning |
|---|---|---|
| order_id | int | unique id |
| sequence | int | starts at 1, strictly increasing, assigned ONCE by the producer |
| side | int | `BUY = 0`, `SELL = 1` (import from `engine.models`; do not redefine) |
| price | int | integer ticks (paise) |
| quantity | int | > 0 |
| timestamp_ns | int | optional; informational only, never used for priority |

## Calling the engine
```python
from engine.matching_engine import MatchingEngine
e = MatchingEngine()
trades = e.submit(order_id, side, price, quantity, sequence)   # fast path: plain tuples
trades = e.submit_order(order)                                  # convenience: list[Trade]
# trade = (trade_id, buy_order_id, sell_order_id, price, quantity, sequence)
e.depth(n) -> (bids, asks)     # [(price, total_qty)], best first   (dashboard)
e.best_bid(), e.best_ask(), e.orders_processed, e.trades_executed
```
The Cython engine (Week 2) exposes the same API. `submit()` is what the pipeline should call.

## Rules
1. Limit orders only, single instrument, no cancel/modify.
2. Price priority, then time priority (arrival order == sequence order).
3. **Trades execute at the resting order's price.**
4. An incoming order matches as much as it can; any remainder rests at its limit price.
5. `trade.sequence` is the sequence of the incoming order.

## Errors (the engine fails loudly rather than corrupting the book)
`ValueError` for: bad side, price <= 0, quantity <= 0, or `sequence <=` the last processed
sequence (catches duplicates and reordering from the IPC layer). A rejected order changes nothing.
Gap detection (missing sequences) is the pipeline's job, since the engine can't tell a gap from a filtered order.

## Not handled
Duplicate `order_id`s are not checked (hot-path cost); producers must keep ids unique.
