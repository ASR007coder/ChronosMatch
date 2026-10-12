"""
Unit tests for simulator/order_generator.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest
from simulator.order_generator import BUY, SELL, Order, OrderGenerator, SimulatorConfig


def test_generates_requested_count():
    gen = OrderGenerator(SimulatorConfig(seed=1))
    assert len(gen.generate(50)) == 50


def test_ids_are_unique():
    gen = OrderGenerator(SimulatorConfig(seed=1))
    ids = [o.order_id for o in gen.generate(1000)]
    assert len(set(ids)) == 1000


def test_sequence_strictly_increasing():
    gen = OrderGenerator(SimulatorConfig(seed=1))
    seqs = [o.sequence for o in gen.generate(100)]
    assert seqs == list(range(1, 101))


def test_sequence_starts_at_one():
    gen = OrderGenerator(SimulatorConfig(seed=1))
    first = gen.next_order()
    assert first.sequence == 1
    assert first.order_id == 1


def test_all_sides_valid():
    gen = OrderGenerator(SimulatorConfig(seed=1))
    for o in gen.generate(500):
        assert o.side in (BUY, SELL)


def test_price_within_bounds():
    cfg = SimulatorConfig(seed=1, min_price_ticks=10_000, max_price_ticks=20_000)
    gen = OrderGenerator(cfg)
    for o in gen.generate(500):
        assert 10_000 <= o.price <= 20_000


def test_quantity_within_bounds():
    cfg = SimulatorConfig(seed=1, min_quantity=5, max_quantity=10)
    gen = OrderGenerator(cfg)
    for o in gen.generate(500):
        assert 5 <= o.quantity <= 10


def test_same_seed_reproducible():
    cfg = SimulatorConfig(seed=1234)
    assert OrderGenerator(cfg).generate(50) == OrderGenerator(cfg).generate(50)


def test_different_seed_differs():
    a = OrderGenerator(SimulatorConfig(seed=1)).generate(50)
    b = OrderGenerator(SimulatorConfig(seed=2)).generate(50)
    assert a != b


def test_timestamps_monotonic():
    gen = OrderGenerator(SimulatorConfig(seed=1))
    ts = [o.timestamp_ns for o in gen.generate(100)]
    assert ts == sorted(ts)
    assert len(set(ts)) == 100


def test_negative_count_rejected():
    gen = OrderGenerator(SimulatorConfig(seed=1))
    with pytest.raises(ValueError):
        gen.generate(-1)


def test_zero_count_returns_empty():
    gen = OrderGenerator(SimulatorConfig(seed=1))
    assert gen.generate(0) == []


def test_iterator_protocol():
    gen = OrderGenerator(SimulatorConfig(seed=1))
    assert next(gen).sequence == 1
    assert next(gen).sequence == 2


if __name__ == "__main__":
    test_generates_requested_count()
    test_ids_are_unique()
    test_sequence_strictly_increasing()
    test_sequence_starts_at_one()
    test_all_sides_valid()
    test_price_within_bounds()
    test_quantity_within_bounds()
    test_same_seed_reproducible()
    test_different_seed_differs()
    test_timestamps_monotonic()
    test_negative_count_rejected()
    test_zero_count_returns_empty()
    test_iterator_protocol()
    print("All tests passed (standalone)")