import pytest

from backend.engine.cython.order_book_core import CythonPriceLevel


def test_append_and_peek():
    level = CythonPriceLevel()

    level.append(101, 10)
    level.append(102, 20)

    assert level.peek() == (101, 10)
    assert level.order_count() == 2


def test_fifo_pop():
    level = CythonPriceLevel()

    level.append(101, 10)
    level.append(102, 20)

    assert level.pop_front() == (101, 10)
    assert level.pop_front() == (102, 20)
    assert level.is_empty()


def test_partial_fill():
    level = CythonPriceLevel()

    level.append(101, 10)
    level.update_front_quantity(4)

    assert level.peek() == (101, 4)


def test_empty_pop_raises():
    level = CythonPriceLevel()

    with pytest.raises(IndexError):
        level.pop_front()
        