
# tests/test_ipc_protocol.py


import pytest
import struct

from ipc.protocol import (
    BUY,
    SELL,
    ORDER_RECORD_SIZE,
    encode,
    decode,
    validate_record,
)


def test_round_trip():
    expected = (1001, 1, 50000, 123456789, 100, BUY)

    record = encode(
        order_id=1001,
        sequence=1,
        price=50000,
        timestamp_ns=123456789,
        quantity=100,
        side=BUY,
    )

    assert len(record) == 64
    assert len(record) == ORDER_RECORD_SIZE
    assert decode(record) == expected


def test_sell_side_round_trip():
    record = encode(1001, 1, 50000, 123456789, 100, SELL)
    assert decode(record)[5] == SELL


def test_rejects_wrong_record_lengths():
    with pytest.raises(ValueError):
        validate_record(bytes(63))

    with pytest.raises(ValueError):
        validate_record(bytes(65))


def test_rejects_non_bytes():
    with pytest.raises(TypeError):
        validate_record("not bytes")


@pytest.mark.parametrize(
    "field,value",
    [
        ("sequence", 0),
        ("price", 0),
        ("quantity", 0),
        ("side", 2),
        ("order_id", -1),
        ("sequence", 2**64),
        ("price", 2**63),
        ("timestamp_ns", 2**64),
        ("quantity", 2**32),
    ],
)
def test_rejects_invalid_fields(field, value):
    order = {
        "order_id": 1001,
        "sequence": 1,
        "price": 50000,
        "timestamp_ns": 123456789,
        "quantity": 100,
        "side": BUY,
    }

    order[field] = value

    with pytest.raises((ValueError, TypeError, struct.error)):
        encode(**order)


def test_maximum_sequence_is_supported():
    record = encode(
        order_id=1001,
        sequence=2**64 - 1,
        price=50000,
        timestamp_ns=123456789,
        quantity=100,
        side=BUY,
    )

    assert decode(record)[1] == 2**64 - 1


def test_next_sequence_value_is_rejected():
    with pytest.raises(ValueError):
        encode(1001, 2**64, 50000, 123456789, 100, BUY)