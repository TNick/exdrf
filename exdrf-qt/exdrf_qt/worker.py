import logging
import threading
from queue import Empty, Queue
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, overload
from uuid import uuid4

import sqlparse
from attrs import define, field
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from sqlalchemy import Select

if TYPE_CHECKING:
    from exdrf_al.connection import DbConn
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@define
class Work:
    """A piece of work to be done by the worker thread.

    Attributes:
        statement: The SQLAlchemy select statement to execute.
        callback: The callback function to call with the result.
        req_id: The request ID to identify the work.
    """

    statement: "Select"
    callback: Callable[["Work"], None]
    req_id: Any
    result: List[Any] = field(factory=list)
    error: Any = field(default=None)
    use_unique: bool = False

    def perform(self, session: "Session") -> None:
        """Perform the work."""
        if self.use_unique:
            self.result = list(session.scalars(self.statement).unique().all())
        else:
            self.result = list(session.scalars(self.statement))
        session.expunge_all()


class Relay(QObject):
    """A class that lives in the main thread and is informed about the
    completion of the worker thread.
    """

    worker: "Worker"
    data: Dict[Any, Work]
    queue: Queue

    def __init__(self, cn: "DbConn", parent: Optional[QObject] = None):
        super().__init__(parent)
        self.data = {}
        self.queue = Queue()
        self.worker = Worker(queue=self.queue, cn=cn, parent=self)
        self.worker.haveResult.connect(self.handle_result)

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
            logger.debug("Work with ID %s completed successfully", work_id)
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
        if self.worker.isRunning():
            self.worker.should_stop = True
            self.worker.quit()
            self.worker.wait()

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
        if not self.worker.isRunning():
            self.worker.start()

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

    Attributes:
        queue: The queue to read from.
        should_stop: A flag to indicate if the worker should stop. It is set
            by the relay through the `stop()` method.
        cn: The database connection to use.

    Signals:
        haveResult: Emitted when the worker has a result to send to the relay.
    """

    queue: Queue
    should_stop: bool
    cn: "DbConn"

    haveResult = pyqtSignal(object)

    def __init__(
        self, queue: Queue, cn: "DbConn", parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self.should_stop = False
        self.queue = queue
        self.cn = cn
        self.setObjectName("ExdrfWorkerThread")

    def run(self) -> None:
        """The main function of the worker thread."""
        threading.current_thread().name = "ExdrfWorkerThread"
        while not self.should_stop:
            try:
                work: "Work" = self.queue.get(timeout=0.5)
            except Empty:
                continue

            try:
                with self.cn.session() as session:
                    work.perform(session)
                logger.debug("Work with ID %s completed", work.req_id)
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

            self.haveResult.emit(work.req_id)
