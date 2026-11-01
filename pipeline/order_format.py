"""
ChronosMatch — Member 2: Order Pipeline
64-byte binary wire format for orders.

Format string: "<QQqQIB27x"
    Q  order_id      (uint64)
    Q  sequence      (uint64)   starts at 1, +1 per order
    q  price         (int64)    integer paise (10100 = Rs 101.00)
    Q  timestamp_ns  (uint64)   nanoseconds since epoch
    I  quantity      (uint32)
    B  side          (uint8)    0 = BUY, 1 = SELL
    27x padding                 reserved, zero-filled

Total: 64 bytes per record.
See docs/order-format.md for the full specification.
"""

import struct

try:
    from engine.models import BUY, SELL
except ImportError:
    BUY = 0
    SELL = 1


ORDER_FMT = "<QQqQIB27x"
ORDER_SIZE = struct.calcsize(ORDER_FMT)
assert ORDER_SIZE == 64, f"ORDER_FMT must be 64 bytes, got {ORDER_SIZE}"


def encode(order_id: int,
           sequence: int,
           price: int,
           timestamp_ns: int,
           quantity: int,
           side: int) -> bytes:
    """Serialize one order into exactly 64 bytes."""
    if side not in (BUY, SELL):
        raise ValueError(f"side must be BUY ({BUY}) or SELL ({SELL}), got {side!r}")

    if order_id < 0 or sequence < 1 or quantity < 0:
        raise ValueError("order_id, sequence, quantity must be non-negative")

    try:
        return struct.pack(
            ORDER_FMT,
            order_id,
            sequence,
            price,
            timestamp_ns,
            quantity,
            side,
        )
    except struct.error as e:
        raise ValueError(f"field out of range: {e}") from e


def decode(record: bytes) -> tuple:
    """
    Deserialize a 64-byte record.

    Returns:
        (order_id, sequence, price, timestamp_ns, quantity, side)
    """
    if len(record) != ORDER_SIZE:
        raise ValueError(
            f"record must be {ORDER_SIZE} bytes, got {len(record)}"
        )

    (order_id,
     sequence,
     price,
     timestamp_ns,
     quantity,
     side) = struct.unpack(ORDER_FMT, record)

    return (order_id, sequence, price, timestamp_ns, quantity, side)


if __name__ == "__main__":
    print(f"ORDER_FMT  = {ORDER_FMT!r}")
    print(f"ORDER_SIZE = {ORDER_SIZE} bytes")
    print(f"BUY={BUY}  SELL={SELL}")

    sample = dict(
        order_id=1001,
        sequence=1,
        price=10100,
        timestamp_ns=1_700_000_000_000_000_000,
        quantity=25,
        side=BUY,
    )
    rec = encode(**sample)
    assert len(rec) == 64, f"expected 64 bytes, got {len(rec)}"
    back = decode(rec)
    expected = (
        sample["order_id"],
        sample["sequence"],
        sample["price"],
        sample["timestamp_ns"],
        sample["quantity"],
        sample["side"],
    )
    assert back == expected, f"round-trip mismatch: {back} != {expected}"

    try:
        decode(rec[:-1])
        raise AssertionError("expected ValueError on truncated record")
    except ValueError:
        pass

    print("order_format.py self-test OK")
