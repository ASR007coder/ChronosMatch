

# ipc/protocol.py

import struct

ORDER_RECORD_SIZE = 64

BUY = 0
SELL = 1

# Q: unsigned 64-bit integer
# Q: unsigned 64-bit integer
# q: signed 64-bit integer
# Q: unsigned 64-bit integer
# I: unsigned 32-bit integer
# B: unsigned 8-bit integer
# 27x: 27 reserved padding bytes


ORDER_STRUCT = struct.Struct("<QQqQIB27x")

assert ORDER_STRUCT.size == ORDER_RECORD_SIZE


def encode(
    order_id: int,
    sequence: int,
    price: int,
    timestamp_ns: int,
    quantity: int,
    side: int,
) -> bytes:
    """Validate and encode an order into exactly 64 bytes."""

    values = {
        "order_id": order_id,
        "sequence": sequence,
        "price": price,
        "timestamp_ns": timestamp_ns,
        "quantity": quantity,
        "side": side,
    }

    for name, value in values.items():
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an integer")

    if not 0 <= order_id <= 2**64 - 1:
        raise ValueError("order_id must fit in an unsigned 64-bit integer")

    if not 1 <= sequence <= 2**64 - 1:
        raise ValueError("sequence must be between 1 and 2**64 - 1")

    if not 1 <= price <= 2**63 - 1:
        raise ValueError("price must be a positive signed 64-bit integer")

    if not 0 <= timestamp_ns <= 2**64 - 1:
        raise ValueError("timestamp_ns must fit in an unsigned 64-bit integer")

    if not 1 <= quantity <= 2**32 - 1:
        raise ValueError("quantity must be between 1 and 2**32 - 1")

    if side not in (BUY, SELL):
        raise ValueError("side must be BUY (0) or SELL (1)")

    return ORDER_STRUCT.pack(
        order_id,
        sequence,
        price,
        timestamp_ns,
        quantity,
        side,
    )


def validate_record(record: bytes) -> bytes:
    """Check that a record is bytes of exactly 64 bytes."""

    if not isinstance(record, bytes):
        raise TypeError("record must be bytes")

    if len(record) != ORDER_RECORD_SIZE:
        raise ValueError(
            f"record must be {ORDER_RECORD_SIZE} bytes, got {len(record)}"
        )

    return record


def decode(record: bytes) -> tuple[int, int, int, int, int, int]:
    """Decode a 64-byte record into its six order fields."""

    validate_record(record)

    order_id, sequence, price, timestamp_ns, quantity, side = (
        ORDER_STRUCT.unpack(record)
    )

    # Padding is not returned by struct.unpack.
    # Validate the decoded fields as well.
    if order_id < 0:
        raise ValueError("order_id cannot be negative")

    if sequence < 1:
        raise ValueError("sequence must be at least 1")

    if price <= 0:
        raise ValueError("price must be positive")

    if quantity < 1:
        raise ValueError("quantity must be positive")

    if side not in (BUY, SELL):
        raise ValueError("invalid side")

    return (
        order_id,
        sequence,
        price,
        timestamp_ns,
        quantity,
        side,
    )

























