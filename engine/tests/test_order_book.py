import pytest

from engine.models import BUY, SELL, Order, Trade
from engine.order_book import BookSide, OrderBook


def test_valid_order_can_be_created():
    o = Order(order_id=1, sequence=1, side=BUY, price=10100, quantity=50)
    assert (o.order_id, o.side, o.price, o.quantity, o.timestamp_ns) == (1, BUY, 10100, 50, 0)


@pytest.mark.parametrize("qty", [0, -1])
def test_non_positive_quantity_rejected(qty):
    with pytest.raises(ValueError):
        Order(1, 1, BUY, 100, qty)


@pytest.mark.parametrize("price", [0, -5])
def test_non_positive_price_rejected(price):
    with pytest.raises(ValueError):
        Order(1, 1, BUY, price, 10)


@pytest.mark.parametrize("side", [2, -1, 99])
def test_invalid_side_rejected(side):
    with pytest.raises(ValueError):
        Order(1, 1, side, 100, 10)


def test_float_price_rejected():
    with pytest.raises(ValueError):
        Order(1, 1, BUY, 101.5, 10)


def test_trade_is_a_plain_comparable_tuple():
    assert Trade(1, 2, 3, 100, 5, 9) == (1, 2, 3, 100, 5, 9)


def test_empty_book():
    book = OrderBook()
    assert book.best_bid() is None and book.best_ask() is None
    assert book.depth() == ([], [])
    assert book.bids.is_empty() and book.asks.is_empty()


def test_bid_side_orders_levels_high_to_low_and_keeps_fifo():
    side = BookSide(is_bid=True)
    side.rest(100, 1, 5)
    side.rest(102, 2, 7)
    side.rest(100, 3, 4)
    assert side.best_price() == 102
    assert side.depth(5) == [(102, 7), (100, 9)]
    assert [o[0] for o in side.levels[100]] == [1, 3]   # arrival order preserved
    assert side.order_count() == 3


def test_ask_side_orders_levels_low_to_high_and_pops_best():
    side = BookSide(is_bid=False)
    side.rest(103, 1, 5)
    side.rest(101, 2, 7)
    assert side.best_price() == 101
    side.levels[101].clear()
    side.pop_best()
    assert side.best_price() == 103
    side.levels[103].clear()
    side.pop_best()
    assert side.best_price() is None
