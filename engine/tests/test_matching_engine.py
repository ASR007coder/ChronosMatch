import random

import pytest

from engine.models import BUY, SELL, Order, Trade
from engine.tests.oracle import NaiveEngine


def test_brief_example_partial_fills(engine):
    # A: BUY 10 @ 101 rests. B: SELL 6 @ 100 hits it; trade at the RESTING price 101.
    assert engine.submit(1, BUY, 101, 10, 1) == []
    assert engine.submit(2, SELL, 100, 6, 2) == [(1, 1, 2, 101, 6, 2)]
    # C: SELL 8 @ 101 matches A's last 4, then rests with 4.
    assert engine.submit(3, SELL, 101, 8, 3) == [(2, 1, 3, 101, 4, 3)]
    assert engine.depth() == ([], [(101, 4)])


def test_price_time_priority(engine):
    engine.submit(1, SELL, 100, 5, 1)    # A
    engine.submit(2, SELL, 100, 8, 2)    # B: same price, later
    engine.submit(3, SELL, 101, 10, 3)   # C: worse price
    assert engine.submit(4, BUY, 100, 9, 4) == [(1, 4, 1, 100, 5, 4), (2, 4, 2, 100, 4, 4)]
    assert engine.depth()[1] == [(100, 4), (101, 10)]


def test_sweeps_multiple_levels_best_price_first(engine):
    engine.submit(1, SELL, 103, 12, 1)
    engine.submit(2, SELL, 102, 8, 2)
    trades = engine.submit(3, BUY, 105, 15, 3)
    assert [(t[3], t[4]) for t in trades] == [(102, 8), (103, 7)]
    assert engine.depth() == ([], [(103, 5)])


def test_remainder_rests_when_limit_not_reached(engine):
    engine.submit(1, SELL, 102, 8, 1)
    engine.submit(2, SELL, 103, 12, 2)
    trades = engine.submit(3, BUY, 102, 12, 3)
    assert len(trades) == 1 and trades[0][4] == 8
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
    assert [(t[1], t[3], t[4]) for t in trades] == [(2, 100, 5), (1, 99, 2)]


def test_exact_fill_removes_order_and_level(engine):
    engine.submit(1, SELL, 100, 5, 1)
    engine.submit(2, BUY, 100, 5, 2)
    assert engine.depth() == ([], [])
    assert engine.best_bid() is None and engine.best_ask() is None


def test_submit_order_wrapper_returns_trade_objects(engine):
    engine.submit_order(Order(1, 1, SELL, 100, 5))
    trades = engine.submit_order(Order(2, 2, BUY, 100, 3))
    assert trades == [Trade(1, 2, 1, 100, 3, 2)]
    assert trades[0].price == 100


def test_counters(engine):
    engine.submit(1, SELL, 100, 5, 1)
    engine.submit(2, BUY, 100, 5, 2)
    assert (engine.orders_processed, engine.trades_executed) == (2, 1)


@pytest.mark.parametrize("args", [(1, BUY, 100, 0, 1), (1, BUY, 100, -5, 1),
                                  (1, BUY, 0, 5, 1), (1, 7, 100, 5, 1)])
def test_invalid_orders_rejected(engine, args):
    with pytest.raises(ValueError):
        engine.submit(*args)


def test_duplicate_or_out_of_order_sequence_rejected(engine):
    engine.submit(1, BUY, 100, 5, 5)
    with pytest.raises(ValueError):
        engine.submit(2, SELL, 100, 5, 5)    # duplicate sequence
    with pytest.raises(ValueError):
        engine.submit(3, SELL, 100, 5, 4)    # goes backwards
    assert engine.depth() == ([(100, 5)], [])   # rejected orders left no trace
    assert engine.orders_processed == 1


def test_rejected_order_does_not_consume_sequence(engine):
    with pytest.raises(ValueError):
        engine.submit(1, BUY, 100, 0, 1)
    engine.submit(1, BUY, 100, 5, 1)         # same sequence is still valid


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_matches_naive_oracle_and_invariants(engine_cls, seed):
    rng = random.Random(seed)
    real, oracle = engine_cls(), NaiveEngine()
    submitted = traded = 0
    for seq in range(1, 3001):
        side = rng.choice((BUY, SELL))
        price = rng.randint(95, 105)          # narrow band => lots of crossing
        qty = rng.randint(1, 50)
        got = real.submit(seq, side, price, qty, seq)
        assert got == oracle.submit(seq, side, price, qty, seq)
        submitted += qty
        traded += sum(t[4] for t in got)
        bb, ba = real.best_bid(), real.best_ask()
        assert bb is None or ba is None or bb < ba, "book is crossed"
    bids, asks = real.depth(50)
    assert (bids, asks) == oracle.depth(50)
    resting = sum(q for _, q in bids) + sum(q for _, q in asks)
    assert submitted == 2 * traded + resting   # each traded unit consumes one buy + one sell
