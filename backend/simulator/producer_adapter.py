
from __future__ import annotations

import asyncio
import threading
import time

from queue import Empty, Queue
from typing import Optional, Protocol, Sequence

from backend.simulator.order_generator import Order


class ProducerError(Exception):
    """Base for producer-level failures."""


class ProducerRejected(ProducerError):
    """The producer explicitly rejected an order."""


class ProducerFull(ProducerError):
    """The IPC ring buffer remained full until timeout."""


class IPCProducerLike(Protocol):
    def submit(
        self,
        order_id: int,
        sequence: int,
        price: int,
        timestamp_ns: int,
        quantity: int,
        side: int,
        timeout: Optional[float] = None,
    ) -> bool:
        ...


class IPCProducerAdapter:
    """
    Async bounded producer adapter backed by one synchronous worker.

    The asyncio semaphore is the single source of backpressure.
    The internal thread queue is unbounded, but the semaphore limits
    outstanding orders to queue_capacity, including orders being published.

    The worker publishes batches using submit_many() when available.
    """

    _STOP = object()
    _MAX_RING_BATCH = 64

    def __init__(
        self,
        producer: IPCProducerLike,
        timeout: float = 1.0,
        queue_capacity: int = 4096,
        batch_size: int = 64,
    ) -> None:

        if timeout <= 0:
            raise ValueError("timeout must be positive")

        if queue_capacity <= 0:
            raise ValueError("queue_capacity must be positive")

        if batch_size <= 0:
            raise ValueError("batch_size must be positive")

        self._producer = producer
        self._timeout = timeout
        self._queue_capacity = queue_capacity

        # Producer.submit_many() cannot publish more than ring capacity.
        self._batch_size = min(batch_size, self._MAX_RING_BATCH)

        # Capacity is controlled by _slots, not by Queue(maxsize).
        self._queue: Queue = Queue()

        self._slots: Optional[asyncio.Semaphore] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None

        self._error: Optional[BaseException] = None
        self._error_lock = threading.Lock()

        # queue_wait_seconds is updated by the event-loop thread.
        # publish_seconds and published are updated by the worker.
        # Read these metrics after close(), once both sides have stopped.
        self.queue_wait_seconds = 0.0
        self.publish_seconds = 0.0
        self.published = 0

        self._started = False
        self._closed = False

    def _get_error(self) -> Optional[BaseException]:
        with self._error_lock:
            return self._error

    def _set_error(self, error: BaseException) -> None:
        with self._error_lock:
            if self._error is None:
                self._error = error

    def _release_slots(self, count: int) -> None:
        """Run on the asyncio event-loop thread."""
        slots = self._slots

        if slots is None:
            return

        for _ in range(count):
            slots.release()

    def start(self) -> None:
        if self._started:
            raise RuntimeError("Producer adapter already started")

        if self._closed:
            raise RuntimeError("Producer adapter is closed")

        self._loop = asyncio.get_running_loop()
        self._slots = asyncio.Semaphore(self._queue_capacity)

        self._thread = threading.Thread(
            target=self._worker,
            name="chronosmatch-ipc-producer",
            daemon=False,
        )

        self._thread.start()
        self._started = True

    async def submit(self, order: Order) -> bool:
        if self._closed:
            raise RuntimeError("Producer adapter is closed")

        # Standalone compatibility mode.
        if not self._started:
            start = time.perf_counter()

            try:
                return await asyncio.to_thread(
                    self._producer.submit,
                    order_id=order.order_id,
                    sequence=order.sequence,
                    price=order.price,
                    timestamp_ns=order.timestamp_ns,
                    quantity=order.quantity,
                    side=order.side,
                    timeout=self._timeout,
                )

            except TimeoutError as exc:
                raise ProducerFull(str(exc)) from exc

            except Exception as exc:
                raise ProducerError(str(exc)) from exc

            finally:
                self.publish_seconds += (
                    time.perf_counter() - start
                )

        error = self._get_error()

        if error is not None:
            raise ProducerError(
                "Producer worker failed"
            ) from error

        thread = self._thread
        slots = self._slots

        if thread is None or not thread.is_alive():
            raise ProducerError("Producer worker is not running")

        if slots is None:
            raise RuntimeError("Producer adapter was not initialized")

        queue_wait_start = time.perf_counter()

        await slots.acquire()

        self.queue_wait_seconds += (
            time.perf_counter() - queue_wait_start
        )

        # The worker may have failed while this coroutine waited.
        error = self._get_error()

        if error is not None or not thread.is_alive():
            slots.release()

            raise ProducerError(
                "Producer worker failed"
            ) from error

        try:
            self._queue.put_nowait(order)

        except Exception:
            slots.release()
            raise

        return True

    def _publish_batch(self, orders: Sequence[Order]) -> int:
        submit_many = getattr(
            self._producer,
            "submit_many",
            None,
        )

        if callable(submit_many):
            # Avoid allocating an intermediate list of tuples.
            # Producer.submit_many() consumes this iterable directly.
            batch_data = (
                (
                    order.order_id,
                    order.sequence,
                    order.price,
                    order.timestamp_ns,
                    order.quantity,
                    order.side,
                )
                for order in orders
            )

            published_count = submit_many(batch_data)

            if published_count != len(orders):
                raise ProducerRejected(
                    "Batch publish count mismatch: "
                    f"expected {len(orders)}, "
                    f"published {published_count}"
                )

            return published_count

        # Compatibility fallback for single-order producers.
        published_count = 0

        for order in orders:
            success = self._producer.submit(
                order_id=order.order_id,
                sequence=order.sequence,
                price=order.price,
                timestamp_ns=order.timestamp_ns,
                quantity=order.quantity,
                side=order.side,
                timeout=self._timeout,
            )

            if not success:
                raise ProducerRejected(
                    f"Producer rejected order {order.order_id}"
                )

            published_count += 1

        return published_count

    def _release_batch_capacity(self, count: int) -> None:
        """Schedule capacity release on the event-loop thread."""
        loop = self._loop

        if loop is None or loop.is_closed():
            return

        loop.call_soon_threadsafe(
            self._release_slots,
            count,
        )

    def _worker(self) -> None:
        while True:
            first_item = self._queue.get()

            if first_item is self._STOP:
                self._queue.task_done()
                return

            batch = [first_item]
            stop_after_batch = False

            # Drain currently available orders without waiting
            # for the batch to become full.
            for _ in range(self._batch_size - 1):
                try:
                    item = self._queue.get_nowait()
                except Empty:
                    break

                if item is self._STOP:
                    self._queue.task_done()
                    stop_after_batch = True
                    break

                batch.append(item)

            try:
                if self._get_error() is None:
                    publish_start = time.perf_counter()

                    try:
                        count = self._publish_batch(batch)
                        self.published += count

                    except TimeoutError as exc:
                        self._set_error(
                            ProducerFull(str(exc))
                        )

                    except Exception as exc:
                        if isinstance(exc, ProducerError):
                            self._set_error(exc)
                        else:
                            self._set_error(
                                ProducerError(
                                    f"IPC producer failed: {exc}"
                                )
                            )

                    finally:
                        self.publish_seconds += (
                            time.perf_counter() - publish_start
                        )

            finally:
                for _ in batch:
                    self._queue.task_done()

                self._release_batch_capacity(len(batch))

            if stop_after_batch:
                return

    async def close(self) -> None:
        if not self._started or self._closed:
            return

        self._closed = True

        try:
            thread = self._thread
            slots = self._slots

            if thread is not None and thread.is_alive():
                if slots is None:
                    raise RuntimeError(
                        "Producer adapter was not initialized"
                    )

                # Wait for one capacity slot before inserting STOP.
                # This ensures the sentinel cannot exceed the
                # outstanding-order capacity.
                await slots.acquire()
                self._queue.put_nowait(self._STOP)

            if thread is not None:
                await asyncio.to_thread(thread.join)

        finally:
            error = self._get_error()

        if error is not None:
            raise ProducerError(
                f"IPC producer failed: {error}"
            ) from error
