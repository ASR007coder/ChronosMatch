"""Verify that the Cython source follows Python engine behaviour."""

import random

import pytest

from backend.engine.matching_engine import MatchingEngine
from backend.engine.cython.matching_core import CythonMatchingEngine


def test_python_and_cython_engines_produce_identical_trades():
    python_engine = MatchingEngine()
    cython_engine = CythonMatchingEngine()

    orders = [
        (1, 0, 10000, 10, 1),
        (2, 0, 10100, 5, 2),
        (3, 1, 9900, 7, 3),
        (4, 1, 10000, 4, 4),
        (5, 0, 10000, 10, 5),
    ]

    for order in orders:
        assert python_engine.submit(*order) == cython_engine.submit(*order)

    assert python_engine.depth() == cython_engine.depth()
    assert python_engine.best_bid() == cython_engine.best_bid()
    assert python_engine.best_ask() == cython_engine.best_ask()

    assert python_engine.orders_processed == cython_engine.orders_processed
    assert python_engine.trades_executed == cython_engine.trades_executed


@pytest.mark.parametrize("seed", [11, 22, 33])
def test_python_and_cython_randomized_parity(seed):
    rng = random.Random(seed)

    python_engine = MatchingEngine()
    cython_engine = CythonMatchingEngine()

    for sequence in range(1, 3001):
        order = (
            sequence,
            rng.choice((0, 1)),
            rng.randint(95, 105),
            rng.randint(1, 50),
            sequence,
        )

        python_trades = python_engine.submit(*order)
        cython_trades = cython_engine.submit(*order)

        assert python_trades == cython_trades
        assert python_engine.depth(50) == cython_engine.depth(50)
        assert python_engine.best_bid() == cython_engine.best_bid()
        assert python_engine.best_ask() == cython_engine.best_ask()
        assert python_engine.orders_processed == cython_engine.orders_processed
        assert python_engine.trades_executed == cython_engine.trades_executed


@pytest.mark.parametrize(
    "invalid_order",
    [
        (100, 2, 10000, 10, 3),   # Invalid side
        (100, 0, 0, 10, 3),      # Invalid price
        (100, 0, 10000, 0, 3),   # Invalid quantity
        (100, 0, 10000, 10, 2),  # Duplicate sequence
        (101, 1, 10000, 10, 1),  # Out-of-order sequence
    ],
)
def test_python_and_cython_rejections_preserve_state(invalid_order):
    python_engine = MatchingEngine()
    cython_engine = CythonMatchingEngine()

    initial_orders = [
        (1, 0, 10000, 10, 1),
        (2, 1, 9900, 5, 2),
    ]

    for order in initial_orders:
        assert python_engine.submit(*order) == cython_engine.submit(*order)

    def snapshot(engine):
        return {
            "depth": engine.depth(50),
            "best_bid": engine.best_bid(),
            "best_ask": engine.best_ask(),
            "orders_processed": engine.orders_processed,
            "trades_executed": engine.trades_executed,
        }

    python_before = snapshot(python_engine)
    cython_before = snapshot(cython_engine)

    python_error = None
    cython_error = None

    try:
        python_engine.submit(*invalid_order)
    except (ValueError, TypeError) as exc:
        python_error = type(exc)

    try:
        cython_engine.submit(*invalid_order)
    except (ValueError, TypeError) as exc:
        cython_error = type(exc)

    assert python_error is not None
    assert cython_error is not None
    assert python_error == cython_error

    assert snapshot(python_engine) == python_before
    assert snapshot(cython_engine) == cython_before