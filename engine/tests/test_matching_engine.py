import random

import pytest

from engine.models import BUY, SELL, Order, Trade
from engine.tests.oracle import NaiveEngine


def test_brief_example_partial_fills(engine):
    # A: BUY 10 @ 101 rests. B: SELL 6 @ 100 hits it.
    # Trade executes at the resting order's price: 101.
    assert engine.submit(1, BUY, 101, 10, 1) == []
    assert engine.submit(2, SELL, 100, 6, 2) == [(1, 1, 2, 101, 6, 2)]

    # C: SELL 8 @ 101 matches A's remaining 4, then rests with 4.
    assert engine.submit(3, SELL, 101, 8, 3) == [(2, 1, 3, 101, 4, 3)]
    assert engine.depth() == ([], [(101, 4)])


def test_price_time_priority(engine):
    engine.submit(1, SELL, 100, 5, 1)    # A: first at price 100
    engine.submit(2, SELL, 100, 8, 2)    # B: later at price 100
    engine.submit(3, SELL, 101, 10, 3)   # C: worse price

    assert engine.submit(4, BUY, 100, 9, 4) == [
        (1, 4, 1, 100, 5, 4),
        (2, 4, 2, 100, 4, 4),
    ]

    # B has 4 remaining; C remains untouched.
    assert engine.depth()[1] == [(100, 4), (101, 10)]


def test_sweeps_multiple_levels_best_price_first(engine):
    engine.submit(1, SELL, 103, 12, 1)
    engine.submit(2, SELL, 102, 8, 2)

    trades = engine.submit(3, BUY, 105, 15, 3)

    # Lowest ask executes first.
    assert [(trade[3], trade[4]) for trade in trades] == [
        (102, 8),
        (103, 7),
    ]

    assert engine.depth() == ([], [(103, 5)])


def test_remainder_rests_when_limit_not_reached(engine):
    engine.submit(1, SELL, 102, 8, 1)
    engine.submit(2, SELL, 103, 12, 2)

    trades = engine.submit(3, BUY, 102, 12, 3)

    # The buy limit of 102 must not match the ask at 103.
    assert len(trades) == 1
    assert trades[0][3] == 102
    assert trades[0][4] == 8

    assert engine.depth() == ([(102, 4)], [(103, 12)])


def test_no_cross_means_no_trade(engine):
    engine.submit(1, BUY, 100, 10, 1)
    engine.submit(2, SELL, 102, 8, 2)

    assert engine.depth() == ([(100, 10)], [(102, 8)])
    assert engine.trades_executed == 0


def test_aggressive_sell_hits_highest_bid_first(engine):
    engine.submit(1, BUY, 99, 5, 1)
    engine.submit(2, BUY, 100, 5, 2)

    trades = engine.submit(3, SELL, 99, 7, 3)

    # Highest bid executes first.
    assert [(trade[1], trade[3], trade[4]) for trade in trades] == [
        (2, 100, 5),
        (1, 99, 2),
    ]


def test_exact_fill_removes_order_and_level(engine):
    engine.submit(1, SELL, 100, 5, 1)
    engine.submit(2, BUY, 100, 5, 2)

    assert engine.depth() == ([], [])
    assert engine.best_bid() is None
    assert engine.best_ask() is None


def test_submit_order_wrapper_returns_trade_objects(engine):
    engine.submit_order(Order(1, 1, SELL, 100, 5))

    trades = engine.submit_order(Order(2, 2, BUY, 100, 3))

    assert trades == [Trade(1, 2, 1, 100, 3, 2)]
    assert trades[0].price == 100


def test_counters(engine):
    engine.submit(1, SELL, 100, 5, 1)
    engine.submit(2, BUY, 100, 5, 2)

    assert (engine.orders_processed, engine.trades_executed) == (2, 1)


@pytest.mark.parametrize(
    "args",
    [
        (1, BUY, 100, 0, 1),    # zero quantity
        (1, BUY, 100, -5, 1),   # negative quantity
        (1, BUY, 0, 5, 1),      # zero price
        (1, BUY, -5, 5, 1),     # negative price
        (1, 7, 100, 5, 1),      # invalid side
    ],
)
def test_invalid_orders_rejected(engine, args):
    with pytest.raises(ValueError):
        engine.submit(*args)


@pytest.mark.parametrize(
    "args",
    [
        (2, BUY, 100, 0, 2),    # zero quantity
        (2, BUY, 100, -5, 2),   # negative quantity
        (2, BUY, 0, 5, 2),      # zero price
        (2, BUY, -5, 5, 2),     # negative price
        (2, 7, 100, 5, 2),      # invalid side
    ],
)
def test_invalid_orders_do_not_change_engine_state(engine, args):
    # Establish existing state first.
    engine.submit(1, BUY, 99, 10, 1)

    before_book = engine.depth()
    before_orders = engine.orders_processed
    before_trades = engine.trades_executed

    with pytest.raises(ValueError):
        engine.submit(*args)

    assert engine.depth() == before_book
    assert engine.orders_processed == before_orders
    assert engine.trades_executed == before_trades


def test_duplicate_or_out_of_order_sequence_rejected(engine):
    engine.submit(1, BUY, 100, 5, 5)

    with pytest.raises(ValueError):
        engine.submit(2, SELL, 100, 5, 5)    # duplicate sequence

    with pytest.raises(ValueError):
        engine.submit(3, SELL, 100, 5, 4)    # goes backwards

    assert engine.depth() == ([(100, 5)], [])
    assert engine.orders_processed == 1


def test_rejected_order_does_not_consume_sequence(engine):
    with pytest.raises(ValueError):
        engine.submit(1, BUY, 100, 0, 1)

    # Same sequence remains valid because the prior order was rejected.
    engine.submit(1, BUY, 100, 5, 1)

    assert engine.depth() == ([(100, 5)], [])
    assert engine.orders_processed == 1


def test_out_of_order_sequence_does_not_corrupt_sequence_state(engine):
    engine.submit(1, BUY, 100, 5, 10)

    with pytest.raises(ValueError):
        engine.submit(2, SELL, 100, 5, 9)

    # A sequence greater than the last accepted sequence remains valid.
    assert engine.submit(3, SELL, 101, 5, 11) == []

    assert engine.orders_processed == 2
    assert engine.depth() == ([(100, 5)], [(101, 5)])


def test_incoming_order_is_never_overfilled(engine):
    engine.submit(1, SELL, 100, 3, 1)

    trades = engine.submit(2, BUY, 100, 10, 2)

    assert sum(trade[4] for trade in trades) == 3
    assert engine.depth() == ([(100, 7)], [])


def test_resting_order_keeps_exact_remaining_quantity(engine):
    engine.submit(1, SELL, 100, 10, 1)

    trades = engine.submit(2, BUY, 100, 4, 2)

    assert trades == [(1, 2, 1, 100, 4, 2)]
    assert engine.depth() == ([], [(100, 6)])


def test_orders_match_when_prices_are_exactly_equal(engine):
    engine.submit(1, SELL, 100, 5, 1)

    trades = engine.submit(2, BUY, 100, 5, 2)

    assert trades == [(1, 2, 1, 100, 5, 2)]
    assert engine.depth() == ([], [])


def test_counters_remain_consistent_after_partial_and_full_fills(engine):
    engine.submit(1, SELL, 100, 10, 1)
    assert (engine.orders_processed, engine.trades_executed) == (1, 0)

    engine.submit(2, BUY, 100, 4, 2)
    assert (engine.orders_processed, engine.trades_executed) == (2, 1)

    engine.submit(3, BUY, 100, 6, 3)
    assert (engine.orders_processed, engine.trades_executed) == (3, 2)

    assert engine.depth() == ([], [])


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_matches_naive_oracle_and_invariants(engine_cls, seed):
    rng = random.Random(seed)
    real, oracle = engine_cls(), NaiveEngine()

    submitted = traded = 0

    for seq in range(1, 3001):
        side = rng.choice((BUY, SELL))
        price = rng.randint(95, 105)
        qty = rng.randint(1, 50)

        got = real.submit(seq, side, price, qty, seq)

        assert got == oracle.submit(seq, side, price, qty, seq)

        submitted += qty
        traded += sum(trade[4] for trade in got)

        best_bid = real.best_bid()
        best_ask = real.best_ask()

        assert (
            best_bid is None
            or best_ask is None
            or best_bid < best_ask
        ), "book is crossed"

    bids, asks = real.depth(50)

    assert (bids, asks) == oracle.depth(50)

    resting = sum(qty for _, qty in bids) + sum(qty for _, qty in asks)

    # Each traded unit consumes one buy unit and one sell unit.
    assert submitted == 2 * traded + resting