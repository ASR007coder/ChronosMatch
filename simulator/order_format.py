"""
ChronosMatch — Market Simulator
Binary order format: 64-byte fixed-size record.

Format string: "<QQqQIB27x" (little-endian)

See docs/binary-order-format.md for the team specification.
"""

import struct

from engine.models import BUY, SELL


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
    if order_id < 0:
        raise ValueError(f"order_id must be non-negative, got {order_id}")
    if sequence < 1:
        raise ValueError(f"sequence must start at 1, got {sequence}")
    if price <= 0:
        raise ValueError(f"price must be > 0, got {price}")
    if quantity <= 0:
        raise ValueError(f"quantity must be > 0, got {quantity}")
    if side not in (BUY, SELL):
        raise ValueError(f"side must be BUY ({BUY}) or SELL ({SELL}), got {side}")

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
    """Deserialize a 64-byte record."""
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
    sample = dict(
        order_id=1001,
        sequence=1,
        price=10100,
        timestamp_ns=1_700_000_000_000_000_000,
        quantity=25,
        side=BUY,
    )
    rec = encode(**sample)
    assert len(rec) == 64
    back = decode(rec)
    expected = (
        sample["order_id"], sample["sequence"], sample["price"],
        sample["timestamp_ns"], sample["quantity"], sample["side"],
    )
    assert back == expected

    for bad in (
        dict(order_id=-1, sequence=1, price=100, timestamp_ns=0, quantity=1, side=BUY),
        dict(order_id=1, sequence=0,  price=100, timestamp_ns=0, quantity=1, side=BUY),
        dict(order_id=1, sequence=1,  price=0,   timestamp_ns=0, quantity=1, side=BUY),
        dict(order_id=1, sequence=1,  price=100, timestamp_ns=0, quantity=0, side=BUY),
        dict(order_id=1, sequence=1,  price=100, timestamp_ns=0, quantity=1, side=99),
    ):
        try:
            encode(**bad)
            raise AssertionError(f"expected ValueError for {bad}")
        except ValueError:
            pass

    print("order_format.py self-test OK")