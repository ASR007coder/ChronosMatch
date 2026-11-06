import pytest

from backend.engine.models import (
    INT64_MIN,
    INT64_MAX,
    BUY,
    Order,
)
from backend.engine.matching_engine import MatchingEngine


def test_int64_boundary_order_id_accepted():
    order = Order(
        order_id=INT64_MIN,
        sequence=1,
        side=BUY,
        price=100,
        quantity=10,
    )
    assert order.order_id == INT64_MIN


def test_order_id_above_int64_rejected():
    with pytest.raises(ValueError):
        Order(
            order_id=INT64_MAX + 1,
            sequence=1,
            side=BUY,
            price=100,
            quantity=10,
        )


def test_price_below_int64_rejected():
    with pytest.raises(ValueError):
        Order(
            order_id=1,
            sequence=1,
            side=BUY,
            price=INT64_MAX + 1,
            quantity=10,
        )


def test_timestamp_out_of_range_rejected():
    with pytest.raises(ValueError):
        Order(
            order_id=1,
            sequence=1,
            side=BUY,
            price=100,
            quantity=10,
            timestamp_ns=INT64_MAX + 1,
        )


def test_invalid_submit_does_not_mutate_state():
    engine = MatchingEngine()

    with pytest.raises(ValueError):
        engine.submit(
            INT64_MAX + 1,
            BUY,
            100,
            10,
            1,
        )

    assert engine.orders_processed == 0
    assert engine.trades_executed == 0
    assert engine.best_bid() is None
    assert engine.best_ask() is None