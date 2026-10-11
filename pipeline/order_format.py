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

Rules:
  - BUY / SELL come from engine.models — do not redefine.
  - price is always integer paise, never float.
  - sequence starts at 1 and increments by 1.
"""

import struct

# Lazy import so this module doesn't break if engine isn't on sys.path yet.
try:
    from engine.models import BUY, SELL
except ImportError:
    # Fallback for local testing before engine/ is wired up.
    # Remove this fallback once the engine module is available.
    BUY = 0
    SELL = 1


# ----- Constants --------------------------------------------------------

ORDER_FMT = "<QQqQIB27x"
ORDER_SIZE = struct.calcsize(ORDER_FMT)
assert ORDER_SIZE == 64, f"ORDER_FMT must be 64 bytes, got {ORDER_SIZE}"


# ----- Encode / Decode --------------------------------------------------

def encode(order_id: int,
           sequence: int,
           price: int,
           timestamp_ns: int,
           quantity: int,
           side: int) -> bytes:
    """
    Serialize one order into exactly 64 bytes.

    Raises:
        ValueError: if any field is out of its type range.
    """
    # TODO (Day 2): implement.
    raise NotImplementedError("encode() will be implemented on Day 2")


def decode(record: bytes) -> tuple:
    """
    Deserialize a 64-byte record.

    Returns:
        (order_id, sequence, price, timestamp_ns, quantity, side)

    Raises:
        ValueError: if len(record) != 64.
    """
    # TODO (Day 2): implement.
    raise NotImplementedError("decode() will be implemented on Day 2")


# ----- Self-test --------------------------------------------------------

if __name__ == "__main__":
    print(f"ORDER_FMT  = {ORDER_FMT!r}")
    print(f"ORDER_SIZE = {ORDER_SIZE} bytes")
    print(f"BUY={BUY}  SELL={SELL}")
    assert ORDER_SIZE == 64
    print("order_format.py stub self-check OK")
