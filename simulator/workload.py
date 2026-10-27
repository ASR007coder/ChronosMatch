"""
ChronosMatch — Market Simulator
Reproducible workload generators.

A workload decides WHAT kind of orders to produce:
  - mixed        : random buys/sells across a price band
  - marketable   : prices that cross a reference price (will trade)
  - non_marketable : prices that do NOT cross (build book depth)
  - burst        : a temporary spike in generation rate
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable

from simulator.order_generator import (
    BUY,
    SELL,
    Order,
    OrderGenerator,
    SimulatorConfig,
)


DEFAULT_REFERENCE_PRICE = 10_000   # integer ticks (paise)

MIXED = "mixed"
MARKETABLE = "marketable"
NON_MARKETABLE = "non_marketable"
BURST = "burst"


@dataclass(slots=True)
class WorkloadConfig:
    kind: str = MIXED
    count: int = 1_000
    seed: int = 42

    reference_price: int = DEFAULT_REFERENCE_PRICE

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


def mixed_workload(cfg: WorkloadConfig) -> list[Order]:
    sim_cfg = SimulatorConfig(order_count=cfg.count, seed=cfg.seed)
    gen = OrderGenerator(sim_cfg)
    return gen.generate(cfg.count)


def marketable_workload(cfg: WorkloadConfig) -> list[Order]:
    rng = random.Random(cfg.seed)
    sim_cfg = SimulatorConfig(seed=cfg.seed)
    gen = OrderGenerator(sim_cfg)

    orders = []
    for _ in range(cfg.count):
        side = BUY if rng.random() < 0.5 else SELL
        if side == BUY:
            price = rng.randint(cfg.reference_price + 1, cfg.reference_price + 100)
        else:
            price = rng.randint(cfg.reference_price - 100, cfg.reference_price - 1)

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
    rng = random.Random(cfg.seed)
    sim_cfg = SimulatorConfig(seed=cfg.seed)
    gen = OrderGenerator(sim_cfg)

    orders = []
    for _ in range(cfg.count):
        side = BUY if rng.random() < 0.5 else SELL
        if side == BUY:
            price = rng.randint(cfg.reference_price - 100, cfg.reference_price - 1)
        else:
            price = rng.randint(cfg.reference_price + 1, cfg.reference_price + 100)

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
    window — the timestamps are closer together, meaning the effective 
    submission rate is higher.
    """
    base = mixed_workload(cfg)
    if cfg.burst_length == 0:
        return base

    burst_start = cfg.burst_at
    burst_end = min(cfg.burst_at + cfg.burst_length, len(base))
    if burst_start >= len(base):
        return base

    scale = 1.0 / cfg.burst_multiplier
    prev_ts = base[burst_start].timestamp_ns
    patched = []
    
    for i, o in enumerate(base):
        if burst_start <= i < burst_end:
            if i > burst_start:
                prev_ts = prev_ts + int((o.timestamp_ns - prev_ts) * scale)
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


_BUILDERS: dict[str, Callable[[WorkloadConfig], list[Order]]] = {
    MIXED: mixed_workload,
    MARKETABLE: marketable_workload,
    NON_MARKETABLE: non_marketable_workload,
    BURST: burst_workload,
}


def build_workload(cfg: WorkloadConfig) -> list[Order]:
    return _BUILDERS[cfg.kind](cfg)