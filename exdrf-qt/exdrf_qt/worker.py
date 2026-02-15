import heapq
import logging
import threading
import time
from collections import deque
from queue import Empty
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Deque,
    Dict,
    Hashable,
    List,
    Optional,
    overload,
)
from uuid import uuid4

import sqlparse
from attrs import define, field
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from sqlalchemy import Select

if TYPE_CHECKING:
    from exdrf_al.connection import DbConn
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
VERBOSE = 1


@define(slots=True)
class CompletedWorkStat:
    """Statistics about one completed unit of work.

    Attributes:
        req_id: The request ID of the completed work.
        category: Work category used by the queue (fairness class).
        priority: Work priority used by the queue.
        duration_s: How long the work took in seconds.
        finished_at: The wall-clock timestamp when the work completed.
        results_count: Number of results produced by the statement.
        had_error: Whether the work ended with an error.
        statement_preview: A short string representation of the statement.
    """

    req_id: Any
    category: str
    priority: int
    duration_s: float
    finished_at: float
    results_count: int
    had_error: bool
    statement_preview: str = field(repr=False)


class WorkerStats:
    """Thread-safe statistics collected by a worker thread.

    Attributes:
        _max_history: How many completed work items are stored.
        _lock: Protects all internal state.
        _started_count: Number of work items started.
        _finished_count: Number of work items finished (success or error).
        _error_count: Number of work items finished with error.
        _last_started_at: Wall-clock timestamp of last started work.
        _last_finished_at: Wall-clock timestamp of last finished work.
        _current_req_id: The request id of the work currently being executed.
        _current_started_at: perf_counter value when current work started.
        _current_category: Work category for current work.
        _current_priority: Work priority for current work.
        _durations_s: Last N durations in seconds.
        _history: Last N completed work records.
    """

    _max_history: int
    _lock: threading.Lock
    _started_count: int
    _finished_count: int
    _error_count: int
    _last_started_at: Optional[float]
    _last_finished_at: Optional[float]

    _current_req_id: Any
    _current_started_at: Optional[float]
    _current_category: Optional[str]
    _current_priority: Optional[int]

    _durations_s: Deque[float]
    _history: Deque[CompletedWorkStat]

    def __init__(self, max_history: int = 10) -> None:
        self._max_history = max_history
        self._lock = threading.Lock()

        self._started_count = 0
        self._finished_count = 0
        self._error_count = 0
        self._last_started_at = None
        self._last_finished_at = None

        self._current_req_id = None
        self._current_started_at = None
        self._current_category = None
        self._current_priority = None

        self._durations_s = deque(maxlen=max_history)
        self._history = deque(maxlen=max_history)

    def record_started(self, work: "Work") -> None:
        """Record that a work item has started.

        Args:
            work: The work item that has started.
        """
        with self._lock:
            self._started_count += 1
            self._last_started_at = time.time()
            self._current_req_id = work.req_id
            self._current_started_at = time.perf_counter()
            self._current_category = work.get_category()
            self._current_priority = work.get_priority()

    def record_finished(
        self,
        work: "Work",
        *,
        duration_s: float,
        results_count: int,
        had_error: bool,
        statement_preview: str,
    ) -> None:
        """Record that a work item has finished.

        Args:
            work: The completed work item.
            duration_s: Work duration in seconds.
            results_count: Number of results produced by the work.
            had_error: Whether the work ended with an error.
            statement_preview: Short string for debugging/UI.
        """
        finished_at = time.time()
        with self._lock:
            self._finished_count += 1
            if had_error:
                self._error_count += 1
            self._last_finished_at = finished_at

            self._durations_s.append(duration_s)
            self._history.append(
                CompletedWorkStat(
                    req_id=work.req_id,
                    category=work.get_category(),
                    priority=work.get_priority(),
                    duration_s=duration_s,
                    finished_at=finished_at,
                    results_count=results_count,
                    had_error=had_error,
                    statement_preview=statement_preview,
                )
            )

            self._current_req_id = None
            self._current_started_at = None
            self._current_category = None
            self._current_priority = None

    def snapshot(self) -> dict[str, Any]:
        """Get a read-only snapshot of current statistics.

        Returns:
            A dictionary with counts, current execution info, and last N work
            timings including average.
        """
        with self._lock:
            durations = list(self._durations_s)
            avg = (sum(durations) / len(durations)) if durations else None
            current_elapsed_s = None
            if self._current_started_at is not None:
                current_elapsed_s = (
                    time.perf_counter() - self._current_started_at
                )

            history = [
                {
                    "req_id": h.req_id,
                    "category": h.category,
                    "priority": h.priority,
                    "duration_s": h.duration_s,
                    "finished_at": h.finished_at,
                    "results_count": h.results_count,
                    "had_error": h.had_error,
                    "statement_preview": h.statement_preview,
                }
                for h in self._history
            ]

            return {
                "started_count": self._started_count,
                "finished_count": self._finished_count,
                "error_count": self._error_count,
                "last_started_at": self._last_started_at,
                "last_finished_at": self._last_finished_at,
                "current": {
                    "req_id": self._current_req_id,
                    "category": self._current_category,
                    "priority": self._current_priority,
                    "elapsed_s": current_elapsed_s,
                },
                "last_10": {
                    "durations_s": durations,
                    "avg_duration_s": avg,
                    "history": history,
                },
            }


class WorkQueue:
    """A queue of work to be done by the worker thread."""

    heaps: Dict[Hashable, List[tuple[float, int, "Work"]]]
    active: Deque[Hashable]
    active_set: set[Hashable]
    seq: int
    lock: threading.Lock
    not_empty: threading.Condition

    def __init__(self) -> None:
        self.heaps = {}
        self.active = deque()
        self.active_set = set()
        self.seq = 0
        self.lock = threading.Lock()
        self.not_empty = threading.Condition(self.lock)

    def __len__(self) -> int:
        with self.lock:
            return sum(len(h) for h in self.heaps.values())

    def empty(self) -> bool:
        with self.lock:
            # active implies at least one non-empty class (after cleanup in get)
            return not self.active

    def put(self, item: "Work") -> None:
        cls = item.get_category()
        pr = item.get_priority()

        with self.not_empty:  # holds the same underlying lock
            heap = self.heaps.get(cls)
            if heap is None:
                heap = []
                self.heaps[cls] = heap

            heapq.heappush(heap, (-pr, self.seq, item))
            self.seq += 1

            if cls not in self.active_set:
                self.active.append(cls)
                self.active_set.add(cls)

            self.not_empty.notify()

    def get(self, block: bool = True, timeout: float | None = None) -> "Work":
        with self.not_empty:
            if not block:
                if not self.active:
                    raise Empty("get from empty WorkQueue")
            else:
                if not self.not_empty.wait_for(
                    predicate=lambda: bool(self.active), timeout=timeout
                ):
                    raise TimeoutError("Timed out waiting for item")

            # Clean up any empty classes at the front (defensive)
            while self.active:
                cls = self.active[0]
                heap = self.heaps.get(cls)
                if heap:
                    break
                self.active.popleft()
                self.active_set.discard(cls)

            if not self.active:
                raise Empty("get from empty WorkQueue")

            cls = self.active[0]
            heap = self.heaps[cls]
            _, _, item = heapq.heappop(heap)

            # rotate
            self.active.popleft()
            if heap:
                self.active.append(cls)
            else:
                self.active_set.discard(cls)

            return item

    def peek_class_order(self) -> list[Hashable]:
        with self.lock:
            return list(self.active)

    def sizes_by_class(self) -> dict[Hashable, int]:
        with self.lock:
            return {cls: len(h) for cls, h in self.heaps.items() if h}


@define(slots=True)
class Work:
    """A piece of work to be done by the worker thread.

    Attributes:
        statement: The SQLAlchemy select statement to execute.
        callback: The callback function to call with the result.
        req_id: The request ID to identify the work.
        result: The result of the work.
        error: The error generated by the work.
        use_unique: Whether to use unique() on the result.
    """

    statement: "Select" = field(repr=False)
    callback: Callable[["Work"], None] = field(repr=False)
    req_id: Any
    result: List[Any] = field(factory=list, repr=False)
    error: Any = field(default=None, repr=False)
    use_unique: bool = field(default=False, repr=False)

    def perform(self, session: "Session") -> None:
        """Perform the work."""
        if self.use_unique:
            self.result = list(session.scalars(self.statement).unique().all())
        else:
            self.result = list(session.scalars(self.statement))
        session.expunge_all()

    def get_category(self) -> str:
        """The category for the priority queue.

        The items in same category will be chosen in order of priority.
        """
        return ""

    def get_priority(self) -> int:
        """The priority for the priority queue.

        The items with higher priority will be chosen first.
        """
        return 10


class Relay(QObject):
    """A class that lives in the main thread and is informed about the
    completion of the worker thread.
    """

    workers: List["Worker"]
    data: Dict[Any, Work]
    queue: WorkQueue

    def __init__(
        self,
        cn: "DbConn",
        threads_count: int = 4,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.data = {}
        self.queue = WorkQueue()
        self.workers = []
        for i in range(threads_count):
            worker = Worker(queue=self.queue, cn=cn, parent=self, my_id=str(i))
            worker.haveResult.connect(self.handle_result)
            self.workers.append(worker)

    def handle_result(self, work_id: Any):
        """Handle the result from the worker thread.

        Args:
            work_id: The ID of the work that was completed.
        """
        work = self.data.pop(work_id, None)
        if work is None:
            logger.debug("Work with ID %s not found in data", work_id)
            return

        try:
            work.callback(work)
            logger.log(
                VERBOSE, "Work with ID %s completed successfully", work_id
            )
        except Exception as e:
            if isinstance(e, RuntimeError) and "has been deleted" in str(e):
                logger.debug(
                    "Work with ID %s completed, but the callback receiver "
                    "has been deleted.",
                    work_id,
                )
            else:
                logger.error(
                    "Exception while handling the work result: %s",
                    e,
                    exc_info=True,
                )

    def stop(self):
        """Stop the worker thread."""
        for worker in self.workers:
            if worker.isRunning():
                worker.should_stop = True
                worker.quit()
        for worker in self.workers:
            if worker.isRunning():
                worker.wait()

    def debug_snapshot(self) -> dict[str, Any]:
        """Collect a detailed snapshot for debugging/UI.

        Returns:
            A nested dictionary describing queue state and worker states.
        """
        return {
            "queue": {
                "total_len": len(self.queue),
                "class_order": self.queue.peek_class_order(),
                "sizes_by_class": self.queue.sizes_by_class(),
            },
            "workers": [
                {
                    "id": w.my_id,
                    "object_name": w.objectName(),
                    "is_running": w.isRunning(),
                    "should_stop": w.should_stop,
                    "current_work_req_id": getattr(w.work, "req_id", None),
                    "current_work_category": (
                        w.work.get_category() if w.work is not None else None
                    ),
                    "current_work_priority": (
                        w.work.get_priority() if w.work is not None else None
                    ),
                    "current_work_statement": (
                        str(w.work.statement) if w.work is not None else None
                    ),
                    "stats": w.get_stats_snapshot(),
                }
                for w in self.workers
            ],
        }

    @overload
    def push_work(self, work: "Work") -> "Work": ...

    @overload
    def push_work(
        self,
        statement: "Select",
        callback: Callable[["Work"], None],
        req_id: Optional[Any] = None,
        use_unique: bool = False,
    ) -> "Work": ...

    def push_work(  # type: ignore[misc, assignment]
        self,
        statement_or_work: Any,
        callback: Any = None,
        req_id: Optional[Any] = None,
        use_unique: bool = False,
    ) -> "Work":
        """Add work to be done by the worker thread.

        Args:
            statement_or_work: Either a SQLAlchemy select statement or a Work
                object. If a Work object is provided, other parameters are
                ignored.
            callback: The callback function to call with the result. Required
                if statement_or_work is a Select statement.
            req_id: An optional request ID to identify the work. If one is not
                provided, a new one will be generated.
            use_unique: Whether to use unique() on the result.
        """
        for worker in self.workers:
            if not worker.isRunning():
                worker.start()
                break

        # Handle the case where a Work object is passed directly.
        if isinstance(statement_or_work, Work):
            work = statement_or_work
        else:
            # Create the work object from individual parameters.
            if callback is None:
                raise TypeError("callback is required when passing a statement")
            work = Work(
                statement=statement_or_work,
                callback=callback,
                req_id=req_id or uuid4().int,
                use_unique=use_unique,
            )

        # Save it locally.
        self.data[work.req_id] = work

        # Put it in the queue.
        self.queue.put(work)

        return work


class Worker(QThread):
    """The worker that reads the data from the database and emits the results
    to the relay object.

    The worker implements a priority queue to process the work in the order
    of priority among their classes.

    Attributes:
        queue: The queue to read from.
        should_stop: A flag to indicate if the worker should stop. It is set
            by the relay through the `stop()` method.
        cn: The database connection to use.

    Signals:
        haveResult: Emitted when the worker has a result to send to the relay.
    """

    queue: WorkQueue
    should_stop: bool
    cn: "DbConn"
    my_id: str
    work: Optional["Work"]
    _stats: WorkerStats

    haveResult = pyqtSignal(object)

    def __init__(
        self,
        queue: WorkQueue,
        cn: "DbConn",
        my_id: str = "",
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.work = None
        self.my_id = my_id
        self.should_stop = False
        self.queue = queue
        self.cn = cn
        self.setObjectName(f"ExdrfWorkerThread{my_id}")

        # Maintain worker thread statistics for UI/debugging.
        self._stats = WorkerStats(max_history=10)

    def get_stats_snapshot(self) -> dict[str, Any]:
        """Return a thread-safe snapshot of the worker statistics.

        Returns:
            A dictionary suitable for UI/debugging.
        """
        return self._stats.snapshot()

    def run(self) -> None:
        """The main function of the worker thread."""
        threading.current_thread().name = f"ExdrfWorkerThread{self.my_id}"
        while not self.should_stop:
            self.work = None
            try:
                work: "Work" = self.queue.get(timeout=0.5)
                self.work = work
            except (TimeoutError, Empty):
                time.sleep(0.25)
                continue

            # Record that the work has started.
            self._stats.record_started(work)
            work_started = time.perf_counter()

            # Execute the work against the DB.
            try:
                with self.cn.session() as session:
                    work.perform(session)
                logger.log(
                    1,
                    "\n\nWork with ID %s completed in worker thread, "
                    "%d results from statement: %s\n\n",
                    work.req_id,
                    len(work.result),
                    work.statement,
                )
            except Exception as e:
                logger.error(
                    "Error while executing work: %s\n%s",
                    e,
                    sqlparse.format(
                        str(work.statement),
                        reindent=True,
                        keyword_case="upper",
                    ),
                    exc_info=True,
                )
                work.error = e

            # Record completion statistics (even on error).
            duration_s = time.perf_counter() - work_started
            self._stats.record_finished(
                work,
                duration_s=duration_s,
                results_count=len(work.result),
                had_error=bool(work.error),
                statement_preview=str(work.statement),
            )

            self.haveResult.emit(work.req_id)
