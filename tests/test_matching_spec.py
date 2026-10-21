# tests/test_matching_spec.py

import pytest

from engine.matching_engine import MatchingEngine


def make_engine():
    return MatchingEngine()


def submit(engine, order_id, side, price, quantity, sequence):
    return engine.submit(
        order_id=order_id,
        side=side,
        price=price,
        quantity=quantity,
        sequence=sequence,
    )


def test_non_crossing_orders_rest_on_both_sides():
    engine = make_engine()

    assert submit(engine, 1, 0, 100, 5, 1) == []
    assert submit(engine, 2, 1, 105, 3, 2) == []

    bids, asks = engine.depth()

    assert bids == [(100, 5)]
    assert asks == [(105, 3)]


def test_exact_match():
    engine = make_engine()

    submit(engine, 1, 0, 100, 5, 1)

    trades = submit(engine, 2, 1, 100, 5, 2)

    assert trades == [(1, 1, 2, 100, 5, 2)]
    assert engine.depth() == ([], [])


def test_partial_fill_leaves_remaining_quantity():
    engine = make_engine()

    submit(engine, 1, 0, 100, 10, 1)

    trades = submit(engine, 2, 1, 100, 4, 2)

    assert trades == [(1, 1, 2, 100, 4, 2)]

    bids, asks = engine.depth()
    assert bids == [(100, 6)]
    assert asks == []


def test_one_order_matches_multiple_price_levels():
    engine = make_engine()

    submit(engine, 1, 1, 100, 3, 1)
    submit(engine, 2, 1, 101, 4, 2)
    submit(engine, 3, 1, 102, 5, 3)

    trades = submit(engine, 4, 0, 102, 10, 4)

    assert trades == [
        (1, 4, 1, 100, 3, 4),
        (2, 4, 2, 101, 4, 4),
        (3, 4, 3, 102, 3, 4),
    ]

    bids, asks = engine.depth()
    assert bids == []
    assert asks == [(102, 2)]


def test_price_priority_selects_best_ask_first():
    engine = make_engine()

    submit(engine, 1, 1, 102, 2, 1)
    submit(engine, 2, 1, 100, 2, 2)
    submit(engine, 3, 1, 101, 2, 3)

    trades = submit(engine, 4, 0, 105, 6, 4)

    assert trades == [
        (1, 4, 2, 100, 2, 4),
        (2, 4, 3, 101, 2, 4),
        (3, 4, 1, 102, 2, 4),
    ]

    assert engine.depth() == ([], [])


def test_fifo_priority_at_same_price():
    engine = make_engine()

    submit(engine, 10, 1, 100, 2, 1)
    submit(engine, 11, 1, 100, 3, 2)

    trades = submit(engine, 12, 0, 100, 4, 3)

    assert trades == [
        (1, 12, 10, 100, 2, 3),
        (2, 12, 11, 100, 2, 3),
    ]

    bids, asks = engine.depth()
    assert bids == []
    assert asks == [(100, 1)]


@pytest.mark.parametrize(
    "order_id, side, price, quantity, sequence",
    [
        (1, 2, 100, 5, 1),   # Invalid side
        (1, 0, 0, 5, 1),     # Invalid price
        (1, 0, 100, 0, 1),   # Invalid quantity
    ],
)
def test_invalid_order_values_are_rejected_without_mutation(
    order_id, side, price, quantity, sequence
):
    engine = make_engine()
    submit(engine, 10, 0, 100, 5, 1)
    before_depth = engine.depth()

    with pytest.raises(ValueError):
        submit(engine, order_id, side, price, quantity, sequence)

    assert engine.depth() == before_depth


def test_non_increasing_sequence_is_rejected_without_mutation():
    engine = make_engine()
    submit(engine, 1, 0, 100, 5, 2)
    before_depth = engine.depth()

    with pytest.raises(ValueError):
        submit(engine, 2, 1, 100, 5, 2)

    assert engine.depth() == before_depth

def test_empty_book_behavior():
    engine = make_engine()

    assert engine.best_bid() is None
    assert engine.best_ask() is None
    assert engine.depth() == ([], [])


def test_repeated_partial_fills():
    engine = make_engine()

    submit(engine, 1, 1, 100, 10, 1)

    assert submit(engine, 2, 0, 100, 3, 2) == [
        (1, 2, 1, 100, 3, 2)
    ]
    assert engine.depth() == ([], [(100, 7)])

    assert submit(engine, 3, 0, 100, 2, 3) == [
        (2, 3, 1, 100, 2, 3)
    ]
    assert engine.depth() == ([], [(100, 5)])

    assert submit(engine, 4, 0, 100, 5, 4) == [
        (3, 4, 1, 100, 5, 4)
    ]
    assert engine.depth() == ([], [])
def test_order_rests_when_no_counterparty_exists():
    engine = make_engine()

    assert submit(engine, 1, 0, 100, 5, 1) == []

    assert engine.best_bid() == 100
    assert engine.best_ask() is None
    assert engine.depth() == ([(100, 5)], [])
def test_invalid_order_does_not_change_counters():
    engine = make_engine()
    submit(engine, 1, 0, 100, 5, 1)

    before_depth = engine.depth()
    before_orders = engine.orders_processed
    before_trades = engine.trades_executed

    with pytest.raises(ValueError):
        submit(engine, 2, 2, 100, 5, 2)

    assert engine.depth() == before_depth
    assert engine.orders_processed == before_orders
    assert engine.trades_executed == before_trades


def test_incoming_sell_matches_highest_bid_first():
    engine = make_engine()

    submit(engine, 1, 0, 100, 2, 1)
    submit(engine, 2, 0, 102, 3, 2)
    submit(engine, 3, 0, 101, 2, 3)

    trades = submit(engine, 4, 1, 100, 5, 4)

    assert trades == [
        (1, 2, 4, 102, 3, 4),
        (2, 3, 4, 101, 2, 4),
    ]

    assert engine.depth() == ([(100, 2)], [])
