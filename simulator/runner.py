"""
ChronosMatch — Market Simulator
Lifecycle manager that FastAPI can call.

This wraps MarketSimulator with:
  - start() / stop() control
  - status tracking (running, completed, stopped, failed)
  - live stats snapshot
  - run ID for tracking

FastAPI calls this — the simulator itself has no HTTP logic.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from simulator.market_simulator import (
    InMemorySink,
    MarketSimulator,
    SimulatorConfig,
    SimulatorStats,
    OrderSink,
)


# ============================================================
# Run status
# ============================================================

class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


# ============================================================
# SimulatorRun
# ============================================================

class SimulatorRun:
    """
    Lifecycle wrapper around MarketSimulator.

    Usage from FastAPI:

        run = SimulatorRun(config)
        await run.start()               # kicks off async task
        run.status()                    # "running"
        await run.wait()                # optional, await completion
        run.stats()                     # live snapshot
        await run.stop()                # graceful stop
    """

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

    # ----- control ---------------------------------------------------

    async def start(self) -> None:
        """Start the simulator in the background."""
        if self._task is not None:
            raise RuntimeError(f"run {self.run_id} already started")

        self._status = RunStatus.RUNNING
        self._task = asyncio.create_task(self._run())

    async def wait(self) -> SimulatorStats:
        """Wait for the run to finish and return its stats."""
        if self._task is None:
            raise RuntimeError(f"run {self.run_id} not started")
        try:
            return await self._task
        except Exception:
            # Exception already handled inside _run
            raise

    async def stop(self) -> None:
        """Request a graceful stop."""
        self._stop_event.set()
        if self._task is not None and not self._task.done():
            # Give the loop a moment to notice the stop flag
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except asyncio.TimeoutError:
                self._status = RunStatus.FAILED
                self._error = "stop timeout"
                raise

    # ----- introspection ---------------------------------------------

    def status(self) -> RunStatus:
        return self._status

    def stats(self) -> SimulatorStats:
        return self._simulator.stats

    def error(self) -> Optional[str]:
        return self._error

    def snapshot(self) -> dict:
        """A JSON-friendly summary FastAPI can return directly."""
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

    # ----- internal --------------------------------------------------

    async def _run(self) -> SimulatorStats:
        try:
            stats = await self._simulator.run()
            # If we were stopped, mark stopped, otherwise completed
            if self._stop_event.is_set():
                self._status = RunStatus.STOPPED
            else:
                self._status = RunStatus.COMPLETED
            return stats
        except Exception as e:
            self._status = RunStatus.FAILED
            self._error = str(e)
            raise


# ============================================================
# Convenience function for FastAPI
# ============================================================

async def run_simulation(config: SimulatorConfig,
                         sink: Optional[OrderSink] = None) -> dict:
    """
    Run a simulation to completion and return a JSON-friendly snapshot.

    This is the simplest possible interface. FastAPI can call:

        result = await run_simulation(config)
        return result  # dict, ready for JSON
    """
    run = SimulatorRun(config, sink=sink)
    await run.start()
    try:
        await run.wait()
    except Exception:
        pass  # error is captured in run.snapshot()
    return run.snapshot()
