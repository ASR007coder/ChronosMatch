"""
ChronosMatch — Market Simulator
Reproducible workload generators.

A workload decides WHAT kind of orders to produce:
  - mixed        : random buys/sells across a price band
  - marketable   : prices that cross a reference price (will trade)
  - non_marketable : prices that do NOT cross (build book depth)
  - burst        : a temporary spike in generation rate

Each workload is deterministic given a seed, so tests and benchmarks
produce identical order streams.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Iterator

from simulator.order_generator import (
    BUY,
    SELL,
    Order,
    OrderGenerator,
    SimulatorConfig,
)


# ============================================================
# Reference price used to decide "marketable" vs "non-marketable"
# ============================================================

DEFAULT_REFERENCE_PRICE = 10_000   # integer ticks (paise)


# ============================================================
# Workload kinds
# ============================================================

MIXED = "mixed"
MARKETABLE = "marketable"
NON_MARKETABLE = "non_marketable"
BURST = "burst"


# ============================================================
# Config extension for workloads
# ============================================================

@dataclass(slots=True)
class WorkloadConfig:
    kind: str = MIXED
    count: int = 1_000
    seed: int = 42

    # for marketable / non_marketable
    reference_price: int = DEFAULT_REFERENCE_PRICE

    # for burst
    burst_at: int = 500            # start the burst after this many orders
    burst_length: int = 100        # how many orders the burst lasts
    burst_multiplier: int = 5      # instantaneous rate multiplier

    def __post_init__(self):
        if self.kind not in (MIXED, MARKETABLE, NON_MARKETABLE, BURST):
            raise ValueError(f"unknown workload kind: {self.kind!r}")
        if self.count < 0:
            raise ValueError("count must be >= 0")
        if self.reference_price <= 0:
            raise ValueError("reference_price must be > 0")
        if self.burst_at < 0:
            raise ValueError("burst_at must be >= 0")
        if self.burst_length < 0:
            raise ValueError("burst_length must be >= 0")
        if self.burst_multiplier < 1:
            raise ValueError("burst_multiplier must be >= 1")


# ============================================================
# Core workload builders
# ============================================================

def mixed_workload(cfg: WorkloadConfig) -> list[Order]:
    """Random buys and sells across the config's price/quantity band."""
    sim_cfg = SimulatorConfig(
        order_count=cfg.count,
        seed=cfg.seed,
    )
    gen = OrderGenerator(sim_cfg)
    return gen.generate(cfg.count)


def marketable_workload(cfg: WorkloadConfig) -> list[Order]:
    """
    Prices that cross the reference price, so the engine will trade.
    BUY orders priced ABOVE the reference (aggressive buys).
    SELL orders priced BELOW the reference (aggressive sells).
    """
    rng = random.Random(cfg.seed)
    sim_cfg = SimulatorConfig(seed=cfg.seed)
    gen = OrderGenerator(sim_cfg)

    orders = []
    for _ in range(cfg.count):
        side = BUY if rng.random() < 0.5 else SELL
        if side == BUY:
            price = rng.randint(cfg.reference_price + 1,
                                cfg.reference_price + 100)
        else:
            price = rng.randint(cfg.reference_price - 100,
                                cfg.reference_price - 1)

        # Base order fields come from the generator's counters,
        # but we override price + side to make it marketable.
        base = gen.next_order()
        orders.append(Order(
            order_id=base.order_id,
            sequence=base.sequence,
            price=price,
            timestamp_ns=base.timestamp_ns,
            quantity=base.quantity,
            side=side,
        ))
    return orders


def non_marketable_workload(cfg: WorkloadConfig) -> list[Order]:
    """
    Prices that do NOT cross the reference price.
    BUY orders priced BELOW the reference (passive).
    SELL orders priced ABOVE the reference (passive).
    The book builds depth without matching.
    """
    rng = random.Random(cfg.seed)
    sim_cfg = SimulatorConfig(seed=cfg.seed)
    gen = OrderGenerator(sim_cfg)

    orders = []
    for _ in range(cfg.count):
        side = BUY if rng.random() < 0.5 else SELL
        if side == BUY:
            price = rng.randint(cfg.reference_price - 100,
                                cfg.reference_price - 1)
        else:
            price = rng.randint(cfg.reference_price + 1,
                                cfg.reference_price + 100)

        base = gen.next_order()
        orders.append(Order(
            order_id=base.order_id,
            sequence=base.sequence,
            price=price,
            timestamp_ns=base.timestamp_ns,
            quantity=base.quantity,
            side=side,
        ))
    return orders


def burst_workload(cfg: WorkloadConfig) -> list[Order]:
    """
    Normal stream with a temporary spike in rate.
    We model the rate spike by compressing timestamps during the burst
    window — the timestamps are closer together, so the effective rate
    is higher.
    """
    base = mixed_workload(cfg)
    if cfg.burst_length == 0:
        return base

    burst_start = cfg.burst_at
    burst_end = min(cfg.burst_at + cfg.burst_length, len(base))
    if burst_start >= len(base):
        return base

    # Compress timestamps in [burst_start, burst_end) to simulate
    # the "higher rate" window.
    scale = 1.0 / cfg.burst_multiplier
    prev_ts = base[burst_start].timestamp_ns
    patched = []
    for i, o in enumerate(base):
        if burst_start <= i < burst_end:
            prev_ts = prev_ts + int((o.timestamp_ns - prev_ts) * scale) if i > burst_start else prev_ts
            patched.append(Order(
                order_id=o.order_id,
                sequence=o.sequence,
                price=o.price,
                timestamp_ns=prev_ts,
                quantity=o.quantity,
                side=o.side,
            ))
        else:
            patched.append(o)
    return patched


# ============================================================
# Dispatcher
# ============================================================

_BUILDERS: dict[str, Callable[[WorkloadConfig], list[Order]]] = {
    MIXED: mixed_workload,
    MARKETABLE: marketable_workload,
    NON_MARKETABLE: non_marketable_workload,
    BURST: burst_workload,
}


def build_workload(cfg: WorkloadConfig) -> list[Order]:
    """Dispatch to the right workload builder based on cfg.kind."""
    return _BUILDERS[cfg.kind](cfg)


# ============================================================
# Standalone demo
# ============================================================

if __name__ == "__main__":
    for kind in (MIXED, MARKETABLE, NON_MARKETABLE, BURST):
        cfg = WorkloadConfig(kind=kind, count=5, seed=42)
        orders = build_workload(cfg)
        print(f"\n--- {kind} ({len(orders)} orders) ---")
        for o in orders:
            print(" ", o)

    # Reproducibility check
    a = build_workload(WorkloadConfig(kind=MIXED, count=50, seed=42))
    b = build_workload(WorkloadConfig(kind=MIXED, count=50, seed=42))
    assert a == b, "same seed must yield same workload"
    print("\nworkload.py self-test OK")