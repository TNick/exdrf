"""Utilities that replace Qt worker threads with Python threads."""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Optional

from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)
_thread_state = threading.local()


class _CurrentThreadProxy:
    """Expose interruption status for the current managed thread."""

    _event: Optional[threading.Event]

    def __init__(self, event: Optional[threading.Event]) -> None:
        self._event = event

    def isInterruptionRequested(self) -> bool:
        """Tell if interruption was requested for current managed thread."""
        return bool(self._event and self._event.is_set())


class PythonThread(QObject):
    """QObject-compatible worker thread implemented with threading.Thread."""

    started = pyqtSignal()
    finished = pyqtSignal()

    _thread: Optional[threading.Thread]
    _interrupt_event: threading.Event
    _running_lock: threading.Lock

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._thread = None
        self._interrupt_event = threading.Event()
        self._running_lock = threading.Lock()

    @classmethod
    def currentThread(cls) -> _CurrentThreadProxy:
        """Return a proxy exposing interruption status for active worker."""
        event = getattr(_thread_state, "interrupt_event", None)
        return _CurrentThreadProxy(event=event)

    def start(self) -> None:
        """Start the thread if not currently running."""
        with self._running_lock:
            if self._thread is not None and self._thread.is_alive():
                return

            self._interrupt_event.clear()
            thread_name = self.objectName() or self.__class__.__name__
            self._thread = threading.Thread(
                target=self._run_wrapper,
                name=thread_name,
                daemon=True,
            )
            self.started.emit()
            self._thread.start()

    def quit(self) -> None:
        """Request cooperative cancellation."""
        self.requestInterruption()

    def requestInterruption(self) -> None:
        """Request cooperative cancellation."""
        self._interrupt_event.set()

    def isInterruptionRequested(self) -> bool:
        """Tell if cooperative cancellation was requested."""
        return self._interrupt_event.is_set()

    def isRunning(self) -> bool:
        """Tell if thread is alive."""
        with self._running_lock:
            return bool(self._thread and self._thread.is_alive())

    def wait(self, timeout_ms: Optional[int] = None) -> bool:
        """Wait for thread completion, optionally bounded by timeout."""
        with self._running_lock:
            thread = self._thread
        if thread is None:
            return True

        timeout_s: Optional[float] = None
        if timeout_ms is not None:
            timeout_s = max(0.0, timeout_ms / 1000.0)
        thread.join(timeout=timeout_s)
        return not thread.is_alive()

    def _run_wrapper(self) -> None:
        """Set thread-local interruption state and execute run()."""
        _thread_state.interrupt_event = self._interrupt_event
        try:
            self.run()
        except Exception as e:
            logger.error(
                "Unhandled error in PythonThread: %s", e, exc_info=True
            )
            raise
        finally:
            _thread_state.interrupt_event = None
            self.finished.emit()

    def run(self) -> None:
        """Override in subclasses with background logic."""


class WorkerThreadHandle:
    """Run a callable on a Python thread with interruption support."""

    _thread: threading.Thread
    _interrupt_event: threading.Event

    def __init__(
        self,
        target: Callable[[], Any],
        *,
        thread_name: str,
    ) -> None:
        self._interrupt_event = threading.Event()

        def _entry() -> None:
            _thread_state.interrupt_event = self._interrupt_event
            try:
                target()
            finally:
                _thread_state.interrupt_event = None

        self._thread = threading.Thread(
            target=_entry, name=thread_name, daemon=True
        )

    def start(self) -> None:
        """Start worker execution."""
        self._thread.start()

    def requestInterruption(self) -> None:
        """Request cooperative cancellation."""
        self._interrupt_event.set()

    def isInterruptionRequested(self) -> bool:
        """Tell if interruption was requested."""
        return self._interrupt_event.is_set()

    def isRunning(self) -> bool:
        """Tell if worker thread is active."""
        return self._thread.is_alive()

    def wait(self, timeout_ms: Optional[int] = None) -> bool:
        """Wait for completion with optional timeout in milliseconds."""
        timeout_s: Optional[float] = None
        if timeout_ms is not None:
            timeout_s = max(0.0, timeout_ms / 1000.0)
        self._thread.join(timeout=timeout_s)
        return not self._thread.is_alive()

    def quit(self) -> None:
        """Request cooperative cancellation."""
        self.requestInterruption()


def start_worker_thread(
    target: Callable[[], Any],
    *,
    thread_name: str,
) -> WorkerThreadHandle:
    """Create and start a worker thread handle."""
    handle = WorkerThreadHandle(target=target, thread_name=thread_name)
    handle.start()
    return handle
