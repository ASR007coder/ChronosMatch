# Order Format — ChronosMatch

**Owner:** Member 2 (Order Pipeline)
**Status:** Draft (Day 1)
**Binary size:** 64 bytes per order, fixed

---

## Purpose

Defines the wire format used to move orders between pipeline
modules and into the matching engine. Every order crossing the
boundary is encoded as a fixed 64-byte record.

Fixed size means:
- No length prefixes to parse
- Predictable memory layout
- Fast bulk reads / writes
- Easy corruption detection

---

## Struct layout

Python `struct` format: `"<QQqQIB27x"` (little-endian)

| Offset | Size | Format | Field          | Type   | Notes                            |
|-------:|-----:|:------:|:---------------|:-------|:---------------------------------|
| 0      | 8    | `Q`    | `order_id`     | uint64 | Unique, assigned by creator      |
| 8      | 8    | `Q`    | `sequence`     | uint64 | Starts at 1, +1 per order        |
| 16     | 8    | `q`    | `price`        | int64  | Integer paise (10100 = ₹101.00)  |
| 24     | 8    | `Q`    | `timestamp_ns` | uint64 | Nanoseconds since epoch          |
| 32     | 4    | `I`    | `quantity`     | uint32 | Number of shares                 |
| 36     | 1    | `B`    | `side`         | uint8  | 0 = BUY, 1 = SELL                |
| 37     | 27   | `27x`  | `padding`      | —      | Reserved, zero-filled            |
| **64** |      |        |                |        | **Total record size**            |

---

## Rules (from team lead)

1. `BUY = 0`, `SELL = 1` — imported from `engine.models`.
2. Price is an integer in paise (10100 = ₹101.00). Never a float.
3. `sequence` starts at 1, increments by 1 per order.
4. Trade executes at the price of the **resting** order.
5. Engine call:
   `engine.submit(order_id, side, price, quantity, sequence)`
6. Edit only your own files.

---

## Encode / Decode API

In `pipeline/order_format.py`:

    def encode(order_id, sequence, price, timestamp_ns, quantity, side) -> bytes
        # returns exactly 64 bytes

    def decode(record: bytes) -> tuple
        # returns (order_id, sequence, price, timestamp_ns, quantity, side)
        # raises ValueError if len(record) != 64

---

## Example

    order_id     = 1001
    sequence     = 1
    price        = 10100       # ₹101.00 in paise
    timestamp_ns = 1_700_000_000_000_000_000
    quantity     = 25
    side         = BUY         # 0

Encoded → 64 bytes. Decoded → same tuple.

---

## Related files

- `engine/models.py` — defines `BUY`, `SELL`
- `docs/engine-interface.md` — matching engine contract
- `pipeline/order_format.py` — implements this format
