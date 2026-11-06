"""Stress and parity tests for the Cython matching engine."""

import pytest

from backend.engine.matching_engine import MatchingEngine

try:
    from engine.cython.matching_core import CythonMatchingEngine
except ImportError:
    CythonMatchingEngine = None


pytestmark = pytest.mark.skipif(
    CythonMatchingEngine is None,
    reason="Cython extension has not been built",
)


def make_engines():
    return MatchingEngine(), CythonMatchingEngine()


def submit_both(python_engine, cython_engine, order):
    python_trades = python_engine.submit(*order)
    cython_trades = cython_engine.submit(*order)

    assert python_trades == cython_trades


def assert_state_equal(python_engine, cython_engine):
    assert python_engine.depth(10) == cython_engine.depth(10)
    assert python_engine.best_bid() == cython_engine.best_bid()
    assert python_engine.best_ask() == cython_engine.best_ask()

    assert python_engine.orders_processed == cython_engine.orders_processed
    assert python_engine.trades_executed == cython_engine.trades_executed


def test_multiple_price_levels_and_partial_fills():
    python_engine, cython_engine = make_engines()

    orders = [
        # Resting asks at three price levels
        (1, 1, 100, 5, 1),
        (2, 1, 101, 7, 2),
        (3, 1, 102, 4, 3),

        # Buy crosses all three levels, filling 5 + 7 + 3
        (4, 0, 102, 15, 4),
    ]

    for order in orders:
        submit_both(python_engine, cython_engine, order)

    assert_state_equal(python_engine, cython_engine)

    assert python_engine.best_ask() == 102
    assert python_engine.depth(10) == cython_engine.depth(10)


def test_fifo_priority_at_same_price():
    python_engine, cython_engine = make_engines()

    orders = [
        (10, 1, 100, 3, 1),
        (11, 1, 100, 5, 2),
        (12, 1, 100, 4, 3),

        # Should fill order 10 completely, then 2 from order 11
        (13, 0, 100, 5, 4),
    ]

    for order in orders:
        submit_both(python_engine, cython_engine, order)

    assert_state_equal(python_engine, cython_engine)

    python_trades = python_engine.submit(14, 0, 100, 7, 5)
    cython_trades = cython_engine.submit(14, 0, 100, 7, 5)

    assert python_trades == cython_trades
    assert_state_equal(python_engine, cython_engine)


def test_incoming_order_remainder_rests_on_book():
    python_engine, cython_engine = make_engines()

    orders = [
        (20, 1, 100, 4, 1),
        (21, 0, 100, 10, 2),
    ]

    for order in orders:
        submit_both(python_engine, cython_engine, order)

    assert_state_equal(python_engine, cython_engine)

    # The incoming buy should have 6 remaining at 100
    assert python_engine.best_bid() == 100
    assert cython_engine.best_bid() == 100


def test_non_crossing_order_does_not_trade():
    python_engine, cython_engine = make_engines()

    orders = [
        (30, 0, 99, 5, 1),
        (31, 1, 101, 5, 2),
        (32, 0, 100, 3, 3),
    ]

    for order in orders:
        submit_both(python_engine, cython_engine, order)

    assert_state_equal(python_engine, cython_engine)

    assert python_engine.best_bid() == 100
    assert python_engine.best_ask() == 101
    assert python_engine.trades_executed == 0


def test_exact_fill_removes_resting_order():
    python_engine, cython_engine = make_engines()

    orders = [
        (40, 1, 100, 8, 1),
        (41, 0, 100, 8, 2),
    ]

    for order in orders:
        submit_both(python_engine, cython_engine, order)

    assert_state_equal(python_engine, cython_engine)

    assert python_engine.best_ask() is None
    assert cython_engine.best_ask() is None


def test_invalid_order_does_not_mutate_engine_state():
    python_engine, cython_engine = make_engines()

    valid_order = (50, 1, 100, 5, 1)
    submit_both(python_engine, cython_engine, valid_order)

    invalid_orders = [
        (51, 0, 0, 5, 2),   # Invalid price
        (52, 0, 100, 0, 2), # Invalid quantity
        (53, 2, 100, 5, 2), # Invalid side
    ]

    for order in invalid_orders:
        python_before = (
            python_engine.depth(10),
            python_engine.orders_processed,
            python_engine.trades_executed,
        )
        cython_before = (
            cython_engine.depth(10),
            cython_engine.orders_processed,
            cython_engine.trades_executed,
        )

        with pytest.raises(ValueError):
            python_engine.submit(*order)

        with pytest.raises(ValueError):
            cython_engine.submit(*order)

        python_after = (
            python_engine.depth(10),
            python_engine.orders_processed,
            python_engine.trades_executed,
        )
        cython_after = (
            cython_engine.depth(10),
            cython_engine.orders_processed,
            cython_engine.trades_executed,
        )

        assert python_before == python_after
        assert cython_before == cython_after

        assert_state_equal(python_engine, cython_engine)


def test_duplicate_sequence_is_rejected_without_mutation():
    python_engine, cython_engine = make_engines()

    first_order = (60, 0, 100, 5, 1)
    submit_both(python_engine, cython_engine, first_order)

    duplicate_sequence_order = (61, 1, 100, 5, 1)

    python_before = (
        python_engine.depth(10),
        python_engine.orders_processed,
        python_engine.trades_executed,
    )
    cython_before = (
        cython_engine.depth(10),
        cython_engine.orders_processed,
        cython_engine.trades_executed,
    )

    with pytest.raises(ValueError):
        python_engine.submit(*duplicate_sequence_order)

    with pytest.raises(ValueError):
        cython_engine.submit(*duplicate_sequence_order)

    assert python_before == (
        python_engine.depth(10),
        python_engine.orders_processed,
        python_engine.trades_executed,
    )

    assert cython_before == (
        cython_engine.depth(10),
        cython_engine.orders_processed,
        cython_engine.trades_executed,
    )

    assert_state_equal(python_engine, cython_engine)