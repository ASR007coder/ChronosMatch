"""
ChronosMatch — Market Simulator
Lifecycle manager that FastAPI can call.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from simulator.market_simulator import (
    InMemorySink,
    MarketSimulator,
    SimulatorConfig,
    SimulatorStats,
    OrderSink,
)


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


class SimulatorRun:
    def __init__(self,
                 config: SimulatorConfig,
                 sink: Optional[OrderSink] = None,
                 run_id: Optional[str] = None) -> None:
        self.run_id = run_id or uuid.uuid4().hex[:12]
        self.config = config
        self.sink = sink or InMemorySink()
        self._simulator = MarketSimulator(config, self.sink)
        self._status = RunStatus.PENDING
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._error: Optional[str] = None

    async def start(self) -> None:
        if self._task is not None:
            raise RuntimeError(f"run {self.run_id} already started")
        self._status = RunStatus.RUNNING
        self._task = asyncio.create_task(self._run())

    async def wait(self) -> SimulatorStats:
        if self._task is None:
            raise RuntimeError(f"run {self.run_id} not started")
        try:
            return await self._task
        except Exception:
            raise

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None and not self._task.done():
            # We increased the timeout to 10.0 seconds to prevent TimeoutErrors
            try:
                await asyncio.wait_for(self._task, timeout=10.0)
            except asyncio.TimeoutError:
                self._status = RunStatus.FAILED
                self._error = "stop timeout"
                raise

    def status(self) -> RunStatus:
        return self._status

    def stats(self) -> SimulatorStats:
        return self._simulator.stats

    def error(self) -> Optional[str]:
        return self._error

    def snapshot(self) -> dict:
        stats = self._simulator.stats
        return {
            "run_id": self.run_id,
            "status": self._status.value,
            "error": self._error,
            "generated": stats.generated,
            "submitted": stats.submitted,
            "accepted": stats.accepted,
            "rejected": stats.rejected,
            "retried": stats.retried,
            "elapsed_seconds": stats.elapsed_seconds,
            "accepted_rate": stats.accepted_rate,
        }

    async def _run(self) -> SimulatorStats:
        try:
            stats = await self._simulator.run()
            if self._stop_event.is_set():
                self._status = RunStatus.STOPPED
            else:
                self._status = RunStatus.COMPLETED
            return stats
        except Exception as e:
            self._status = RunStatus.FAILED
            self._error = str(e)
            raise


async def run_simulation(config: SimulatorConfig,
                         sink: Optional[OrderSink] = None) -> dict:
    run = SimulatorRun(config, sink=sink)
    await run.start()
    try:
        await run.wait()
    except Exception:
        pass
    return run.snapshot()