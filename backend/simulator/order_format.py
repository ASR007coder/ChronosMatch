
"""
ChronosMatch — Market Simulator
Binary order format: 64-byte fixed-size record.

Format: <QQqQIB27x
"""

import struct

from backend.engine.models import BUY, SELL, INT64_MAX


ORDER_FMT = "<QQqQIB27x"
ORDER_SIZE = struct.calcsize(ORDER_FMT)

UINT32_MAX = (1 << 32) - 1

assert ORDER_SIZE == 64


def _validate_integer(name: str, value: int, minimum: int, maximum: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")

    if value < minimum or value > maximum:
        raise ValueError(
            f"{name} must be between {minimum} and {maximum}, got {value}"
        )


def _validate_order(
    order_id: int,
    sequence: int,
    price: int,
    timestamp_ns: int,
    quantity: int,
    side: int,
) -> None:
    # Keep all 64-bit values compatible with the matching engine.
    _validate_integer("order_id", order_id, 0, INT64_MAX)
    _validate_integer("sequence", sequence, 1, INT64_MAX)
    _validate_integer("price", price, 1, INT64_MAX)
    _validate_integer("timestamp_ns", timestamp_ns, 0, INT64_MAX)
    _validate_integer("quantity", quantity, 1, UINT32_MAX)
    _validate_integer("side", side, BUY, SELL)

    if side not in (BUY, SELL):
        raise ValueError(f"invalid order side: {side}")


def encode(
    order_id: int,
    sequence: int,
    price: int,
    timestamp_ns: int,
    quantity: int,
    side: int,
) -> bytes:
    """Serialize one validated order into exactly 64 bytes."""

    _validate_order(
        order_id,
        sequence,
        price,
        timestamp_ns,
        quantity,
        side,
    )

    return struct.pack(
        ORDER_FMT,
        order_id,
        sequence,
        price,
        timestamp_ns,
        quantity,
        side,
    )


def decode(record: bytes) -> tuple[int, int, int, int, int, int]:
    """Deserialize and validate one 64-byte order record."""

    if not isinstance(record, (bytes, bytearray, memoryview)):
        raise ValueError("record must be bytes-like")

    if len(record) != ORDER_SIZE:
        raise ValueError(
            f"record must be {ORDER_SIZE} bytes, got {len(record)}"
        )

    values = struct.unpack(ORDER_FMT, record)
    _validate_order(*values)

    return values


if __name__ == "__main__":
    sample = {
        "order_id": 1001,
        "sequence": 1,
        "price": 10100,
        "timestamp_ns": 1_700_000_000_000_000_000,
        "quantity": 25,
        "side": BUY,
    }

    record = encode(**sample)
    assert len(record) == ORDER_SIZE
    assert decode(record) == tuple(sample.values())

    print("order_format.py self-test OK")
