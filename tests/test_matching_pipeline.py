# backend/tests/test_matching_pipeline.py


# backend/tests/test_matching_pipeline.py

import pytest

from backend.pipeline.ipc_pipeline import process_orders


def make_order(order_id, sequence, price, quantity, side):
    """Create a deterministic test order."""
    return {
        "order_id": order_id,
        "sequence": sequence,
        "price": price,
        "timestamp_ns": sequence,
        "quantity": quantity,
        "side": side,  # 0 = BUY, 1 = SELL
    }


def test_matching_pipeline_partial_fill():
    """A sell order partially fills a resting buy order."""
    orders = [
        make_order(1, 1, 10000, 5, 0),
        make_order(2, 2, 9900, 3, 1),
    ]

    result = process_orders(orders)

    assert result["orders_received"] == 2
    assert result["orders_processed"] == 2
    assert result["trades_executed"] == 1

    assert result["trades"] == [
        {
            "trade_id": 1,
            "buy_order_id": 1,
            "sell_order_id": 2,
            "price": 10000,
            "quantity": 3,
            "sequence": 2,
        }
    ]

    assert result["order_book"]["bids"] == [(10000, 2)]
    assert result["order_book"]["asks"] == []


def test_matching_pipeline_no_match():
    """Non-crossing buy and sell orders remain in the book."""
    orders = [
        make_order(1, 1, 9900, 5, 0),
        make_order(2, 2, 10100, 3, 1),
    ]

    result = process_orders(orders)

    assert result["orders_processed"] == 2
    assert result["trades_executed"] == 0
    assert result["trades"] == []
    assert result["order_book"]["bids"] == [(9900, 5)]
    assert result["order_book"]["asks"] == [(10100, 3)]


def test_matching_pipeline_full_fill():
    """An incoming sell order fully fills a resting buy order."""
    orders = [
        make_order(1, 1, 10000, 3, 0),
        make_order(2, 2, 9900, 3, 1),
    ]

    result = process_orders(orders)

    assert result["trades_executed"] == 1
    assert result["trades"][0]["buy_order_id"] == 1
    assert result["trades"][0]["sell_order_id"] == 2
    assert result["trades"][0]["price"] == 10000
    assert result["trades"][0]["quantity"] == 3
    assert result["order_book"]["bids"] == []
    assert result["order_book"]["asks"] == []


def test_matching_pipeline_multiple_fills():
    """One incoming buy order matches two resting sell orders."""
    orders = [
        make_order(1, 1, 9900, 2, 1),
        make_order(2, 2, 10000, 3, 1),
        make_order(3, 3, 10000, 4, 0),
    ]

    result = process_orders(orders)

    assert result["trades_executed"] == 2
    assert result["trades"] == [
        {
            "trade_id": 1,
            "buy_order_id": 3,
            "sell_order_id": 1,
            "price": 9900,
            "quantity": 2,
            "sequence": 3,
        },
        {
            "trade_id": 2,
            "buy_order_id": 3,
            "sell_order_id": 2,
            "price": 10000,
            "quantity": 2,
            "sequence": 3,
        },
    ]
    assert result["order_book"]["asks"] == [(10000, 1)]
    assert result["order_book"]["bids"] == []



def test_matching_pipeline_best_price_priority():
    """A buy order matches the lowest-priced sell order first."""
    orders = [
        make_order(1, 1, 10200, 2, 1),
        make_order(2, 2, 10000, 2, 1),
        make_order(3, 3, 10300, 4, 0),
    ]

    result = process_orders(orders)

    assert result["trades_executed"] == 2

    assert result["trades"][0]["sell_order_id"] == 2
    assert result["trades"][0]["price"] == 10000
    assert result["trades"][0]["quantity"] == 2

    assert result["trades"][1]["sell_order_id"] == 1
    assert result["trades"][1]["price"] == 10200
    assert result["trades"][1]["quantity"] == 2

    assert result["order_book"]["asks"] == []
    assert result["order_book"]["bids"] == []


def test_matching_pipeline_time_priority():
    """At the same price, the earlier resting sell order fills first."""
    orders = [
        make_order(1, 1, 10000, 2, 1),
        make_order(2, 2, 10000, 2, 1),
        make_order(3, 3, 10000, 3, 0),
    ]

    result = process_orders(orders)

    assert result["trades_executed"] == 2
    assert result["trades"][0]["sell_order_id"] == 1
    assert result["trades"][0]["quantity"] == 2
    assert result["trades"][1]["sell_order_id"] == 2
    assert result["trades"][1]["quantity"] == 1
    assert result["order_book"]["asks"] == [(10000, 1)]


@pytest.mark.parametrize(
    "order",
    [
        make_order(1, 1, 0, 1, 0),       # Invalid price
        make_order(1, 1, 10000, 0, 0),   # Invalid quantity
        make_order(1, 1, 10000, 1, 2),   # Invalid side
    ],
)
def test_matching_pipeline_rejects_invalid_orders(order):
    """Invalid orders must not be silently accepted."""
    with pytest.raises(ValueError):
        process_orders([order])
