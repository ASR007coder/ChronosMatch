
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


# decoder validation test 



@pytest.mark.parametrize(
    "order_id,sequence,price,timestamp_ns,quantity,side",
    [
        (1001, 0, 50000, 123456789, 100, BUY),  # Invalid sequence
        (1001, 1, 0, 123456789, 100, BUY),      # Invalid price
        (1001, 1, 50000, 123456789, 0, BUY),    # Invalid quantity
        (1001, 1, 50000, 123456789, 100, 2),    # Invalid side
    ],
)
def test_decode_rejects_invalid_fields(
    order_id, sequence, price, timestamp_ns, quantity, side
):
    # Create a 64-byte record directly, bypassing encode() validation.
    record = struct.pack(
        "<QQqQIB27x",
        order_id,
        sequence,
        price,
        timestamp_ns,
        quantity,
        side,
    )

    # Even invalid fields must fit into a correctly sized binary record.
    assert len(record) == ORDER_RECORD_SIZE

    # decode() must reject the invalid field.
    with pytest.raises(ValueError):
        decode(record)




# adding boundary test 


def test_order_id_boundaries():
    # Minimum valid order_id is 0.
    min_record = encode(0, 1, 1, 0, 1, BUY)
    assert decode(min_record)[0] == 0

    # Maximum unsigned 64-bit order_id.
    max_order_id = 2**64 - 1
    max_record = encode(max_order_id, 1, 1, 0, 1, BUY)
    assert decode(max_record)[0] == max_order_id


def test_sequence_boundaries():
    # Minimum valid sequence is 1.
    min_record = encode(1, 1, 1, 0, 1, BUY)
    assert decode(min_record)[1] == 1

    # Maximum unsigned 64-bit sequence.
    max_sequence = 2**64 - 1
    max_record = encode(1, max_sequence, 1, 0, 1, BUY)
    assert decode(max_record)[1] == max_sequence


def test_price_boundaries():
    # Minimum valid price is 1 paise.
    min_record = encode(1, 1, 1, 0, 1, BUY)
    assert decode(min_record)[2] == 1

    # Maximum positive signed 64-bit price.
    max_price = 2**63 - 1
    max_record = encode(1, 1, max_price, 0, 1, BUY)
    assert decode(max_record)[2] == max_price


def test_timestamp_boundaries():
    # Minimum valid timestamp is 0.
    min_record = encode(1, 1, 1, 0, 1, BUY)
    assert decode(min_record)[3] == 0

    # Maximum unsigned 64-bit timestamp.
    max_timestamp = 2**64 - 1
    max_record = encode(1, 1, 1, max_timestamp, 1, BUY)
    assert decode(max_record)[3] == max_timestamp


def test_quantity_boundaries():
    # Minimum valid quantity is 1.
    min_record = encode(1, 1, 1, 0, 1, BUY)
    assert decode(min_record)[4] == 1

    # Maximum unsigned 32-bit quantity.
    max_quantity = 2**32 - 1
    max_record = encode(1, 1, 1, 0, max_quantity, BUY)
    assert decode(max_record)[4] == max_quantity


@pytest.mark.parametrize("side", [BUY, SELL])
def test_valid_sides_round_trip(side):
    record = encode(1, 1, 1, 0, 1, side)
    assert decode(record)[5] == side

































