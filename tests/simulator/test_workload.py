"""
Unit tests for simulator/workload.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest
from simulator.order_generator import BUY, SELL
from simulator.workload import (
    BURST, MARKETABLE, MIXED, NON_MARKETABLE,
    WorkloadConfig, build_workload,
)


def test_mixed_returns_requested_count():
    assert len(build_workload(WorkloadConfig(kind=MIXED, count=100, seed=1))) == 100


def test_mixed_same_seed_reproducible():
    a = build_workload(WorkloadConfig(kind=MIXED, count=50, seed=42))
    b = build_workload(WorkloadConfig(kind=MIXED, count=50, seed=42))
    assert a == b


def test_mixed_different_seed_differs():
    a = build_workload(WorkloadConfig(kind=MIXED, count=50, seed=1))
    b = build_workload(WorkloadConfig(kind=MIXED, count=50, seed=2))
    assert a != b


def test_mixed_count_respected():
    for n in (0, 1, 10, 500):
        assert len(build_workload(WorkloadConfig(kind=MIXED, count=n, seed=1))) == n


def test_marketable_count():
    assert len(build_workload(WorkloadConfig(kind=MARKETABLE, count=50, seed=1))) == 50


def test_marketable_prices_cross_reference():
    ref = 10_000
    cfg = WorkloadConfig(kind=MARKETABLE, count=200, seed=1, reference_price=ref)
    for o in build_workload(cfg):
        if o.side == BUY:
            assert o.price > ref
        else:
            assert o.price < ref


def test_marketable_reproducible():
    a = build_workload(WorkloadConfig(kind=MARKETABLE, count=50, seed=42))
    b = build_workload(WorkloadConfig(kind=MARKETABLE, count=50, seed=42))
    assert a == b


def test_non_marketable_count():
    assert len(build_workload(WorkloadConfig(kind=NON_MARKETABLE, count=50, seed=1))) == 50


def test_non_marketable_prices_do_not_cross():
    ref = 10_000
    cfg = WorkloadConfig(kind=NON_MARKETABLE, count=200, seed=1, reference_price=ref)
    for o in build_workload(cfg):
        if o.side == BUY:
            assert o.price < ref
        else:
            assert o.price > ref


def test_non_marketable_reproducible():
    a = build_workload(WorkloadConfig(kind=NON_MARKETABLE, count=50, seed=42))
    b = build_workload(WorkloadConfig(kind=NON_MARKETABLE, count=50, seed=42))
    assert a == b


def test_burst_count():
    assert len(build_workload(WorkloadConfig(kind=BURST, count=200, seed=1))) == 200


def test_burst_reproducible():
    a = build_workload(WorkloadConfig(kind=BURST, count=200, seed=42))
    b = build_workload(WorkloadConfig(kind=BURST, count=200, seed=42))
    assert a == b


def test_burst_zero_length_is_base():
    cfg = WorkloadConfig(kind=BURST, count=50, seed=1, burst_length=0)
    assert len(build_workload(cfg)) == 50


def test_unknown_kind_rejected():
    with pytest.raises(ValueError):
        WorkloadConfig(kind="garbage", count=10, seed=1)


def test_negative_count_rejected():
    with pytest.raises(ValueError):
        WorkloadConfig(kind=MIXED, count=-1, seed=1)


def test_invalid_reference_price_rejected():
    with pytest.raises(ValueError):
        WorkloadConfig(kind=MIXED, count=10, seed=1, reference_price=0)