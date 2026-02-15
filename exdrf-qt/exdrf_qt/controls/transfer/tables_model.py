"""Table list model with lazy row counts for source/destination panes."""

import logging
import threading
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple

from exdrf_al.connection import DbConn
from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QFont
from sqlalchemy import MetaData, Table, func, inspect, select

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.transfer.count_worker import CountWorker
from exdrf_qt.controls.transfer.tbl_row import TblRow

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

    from exdrf_qt.context import QtContext

logger = logging.getLogger(__name__)
VERBOSE = 1


class TablesModel(QAbstractTableModel, QtUseContext):
    """List model with 2 columns: table name and counts (src/dst).

    The instance is parameterized with which side it represents ("src" or
    "dst"). Counts are displayed as "src_count / dst_count" and are loaded
    lazily in a worker thread on first request.

    Attributes:
        ctx: The application context.

    Private Attributes:
        _side: Either "src" or "dst"; informational only.
        _src_conn: Source connection used to compute counts.
        _dst_conn: Destination connection used to compute counts.
        _rows: Backing storage with table entries.
        _inflight: Map from row index to current worker for that row.
    """

    count_failed = pyqtSignal(str)

    # Public attributes
    ctx: "QtContext"

    # Private attributes
    _side: str
    _src_conn: Optional["DbConn"]
    _dst_conn: Optional["DbConn"]
    _rows: List[TblRow]
    _inflight: Dict[int, CountWorker]

    _pending_lock: threading.Lock
    _pending_rows: List[int]
    _pending_set: Set[int]
    _worker: Optional[CountWorker]

    def __init__(
        self,
        *,
        ctx,
        side: str,
        src_conn: Optional[DbConn] = None,
        dst_conn: Optional[DbConn] = None,
    ) -> None:
        """Initialize the model.

        Args:
            ctx: The application context.
            side: The side of the model ("src" or "dst").
            src_conn: The source connection or None.
            dst_conn: The destination connection or None.
        """
        super().__init__()
        self.ctx = ctx
        assert side in ("src", "dst")
        self._side = side
        self._src_conn = src_conn
        self._dst_conn = dst_conn
        self._rows: List[TblRow] = []
        self._inflight: Dict[int, CountWorker] = {}

        # Ensure worker threads are stopped before model is destroyed
        try:
            self.destroyed.connect(lambda *_: self._stop_all_count_workers())
        except Exception as e:
            logger.error(
                "TablesModel: failed to connect destroyed signal: %s",
                e,
                exc_info=True,
            )
        logger.log(VERBOSE, "TablesModel: initialized side=%s", side)

    # Public API
    def set_connections(
        self, src: Optional["DbConn"], dst: Optional["DbConn"]
    ) -> None:
        """Set the source and destination connections.

        Args:
            src: The source connection or None.
            dst: The destination connection or None.
        """
        self._src_conn = src
        self._dst_conn = dst

    def refresh(self) -> None:
        """Rebuild the table list with names only (lazy counts)."""
        # Stop any ongoing count workers pre-reset to avoid dangling threads
        self._stop_all_count_workers()
        self.beginResetModel()
        self._rows = []
        try:
            src_tables: List[str] = []
            if self._src_conn and self._src_conn.connect():
                assert self._src_conn.engine is not None
                ins = inspect(self._src_conn.engine)
                src_tables = ins.get_table_names(schema=self._src_conn.schema)

            # Build rows using source table list (counts loaded on demand)
            for name in sorted(src_tables):
                self._rows.append(TblRow(name=name))

            logger.log(VERBOSE, "TablesModel.refresh: rows=%d", len(self._rows))
        except Exception as e:
            logger.error("Failed to refresh tables: %s", e, exc_info=True)
        finally:
            self.endResetModel()
            # Pre-queue rows and start worker only when we have a connection
            # for this side
            conn_for_side = (
                self._src_conn if self._side == "src" else self._dst_conn
            )
            if conn_for_side is not None:
                if not hasattr(self, "_pending_lock"):
                    self._pending_lock = threading.Lock()
                    self._pending_rows = []
                    self._pending_set = set()
                with self._pending_lock:
                    self._pending_rows = list(range(len(self._rows)))
                    self._pending_set = set(self._pending_rows)
                try:
                    self._ensure_worker()
                except Exception as e:
                    logger.log(
                        VERBOSE,
                        "TablesModel: failed to ensure worker: %s",
                        e,
                        exc_info=True,
                    )

    # Model API
    def rowCount(
        self, parent: QModelIndex = QModelIndex()
    ) -> int:  # noqa: N802
        """Number of rows in the model.

        Args:
            parent: Required by Qt; unused for flat models.

        Returns:
            Count of table entries.
        """
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(
        self, parent: QModelIndex = QModelIndex()
    ) -> int:  # noqa: N802
        """Number of columns in the model.

        Args:
            parent: Required by Qt; unused for flat models.

        Returns:
            Always 2 (name, counts).
        """
        return 0 if parent.isValid() else 2

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        """Header data for given section/orientation.

        Args:
            section: Section index.
            orientation: Horizontal or Vertical.
            role: Qt data role.

        Returns:
            The header text for display role.
        """
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return [
                self.t("tr.tables.name", "Table"),
                self.t("tr.tables.counts", "Rows"),
            ][section]
        return section + 1

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        """Cell data for requested index/role.

        Args:
            index: The model index.
            role: The Qt data role (defaults to DisplayRole).

        Returns:
            An appropriate value for the role, or None.
        """
        if not index.isValid():
            return None

        row = self._rows[index.row()]
        # Pending state styling (dark gray + italic until counted)
        is_pending = (self._side == "src" and row.cnt_src is None) or (
            self._side == "dst" and row.cnt_dst is None
        )
        if role == Qt.ItemDataRole.FontRole:
            if is_pending:
                f = QFont()
                f.setItalic(True)
                return f
            return None
        if role == Qt.ItemDataRole.ForegroundRole:
            if is_pending:
                return QBrush(QColor(Qt.GlobalColor.darkGray))
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            if index.column() == 0:
                return row.name
            if index.column() == 1:
                need = (
                    row.cnt_src is None
                    if self._side == "src"
                    else row.cnt_dst is None
                )
                if need:
                    self._enqueue_row(index.row())
                    self._ensure_worker()
                val = row.cnt_src if self._side == "src" else row.cnt_dst
                if val is None:
                    return ""
                return "-" if val < 0 else str(val)
        return None

    # Helpers
    def table_name(self, row: int) -> Optional[str]:
        """Get the table name at a given row.

        Args:
            row: Row index.

        Returns:
            Table name or None if out of bounds.
        """
        if 0 <= row < len(self._rows):
            return self._rows[row].name
        return None

    @staticmethod
    def _count_error_is_fatal(exc: Exception) -> bool:
        """Return True if this count error should abort counting for all tables.

        Non-fatal (return False): table not found, missing object; we continue
        with other tables. Fatal (return True): permission denied, schema
        access; we abort and show toast once per connection.
        """
        msg = str(exc).lower()
        if "no such table" in msg or "does not exist" in msg:
            return False
        if "permission denied" in msg or "insufficient privilege" in msg:
            return True
        try:
            if getattr(exc, "pgcode", None) == "42501":
                return True
        except Exception as e:
            logger.log(VERBOSE, "Checking pgcode failed: %s", e, exc_info=True)
        return False

    def _count_with_connection(
        self, db: "Connection", schema: str, table: str
    ) -> Tuple[Optional[int], Optional[str], bool]:
        """Run COUNT(*) for a table using an existing connection
        (no reflection).

        SQLite does not support schema-qualified table names; schema is omitted
        for SQLite so the table name is not prefixed.

        Args:
            db: An open SQLAlchemy Connection (same thread).
            schema: Schema name (ignored for SQLite).
            table: Table name.

        Returns:
            (count, None, False) on success; (None, error_message, is_fatal)
            on failure. When is_fatal is True we abort counting and show toast.
        """
        try:
            # SQLite: do not use schema (no such table: schema.tablename)
            table_schema = (
                None
                if db.engine.dialect.name == "sqlite"
                else (schema if schema else None)
            )
            t = Table(table, MetaData(), schema=table_schema)
            cnt = db.scalar(select(func.count()).select_from(t))
            return (int(cnt or 0), None, False)
        except Exception as e:
            is_fatal = self._count_error_is_fatal(e)
            if is_fatal:
                logger.warning("Count failed for %s.%s: %s", schema, table, e)
            else:
                logger.log(
                    VERBOSE,
                    "Count skipped (table missing or not accessible) %s.%s: %s",
                    schema,
                    table,
                    e,
                )
            # Isolate failed query: roll back so next count runs in a new
            # transaction (e.g. PostgreSQL: "current transaction is aborted")
            try:
                db.rollback()
            except Exception as rb_e:
                logger.log(
                    VERBOSE,
                    "Rollback after count failure failed: %s",
                    rb_e,
                    exc_info=True,
                )
            return (None, str(e), is_fatal)

    def _count_for(self, conn: Optional["DbConn"], table: str) -> Optional[int]:
        """Synchronous count helper used where blocking is acceptable.

        Uses a single connection and no table reflection.

        Args:
            conn: The database connection.
            table: The table name.

        Returns:
            Row count or None if error.
        """
        if conn is None:
            return None

        engine = conn.connect()
        assert engine is not None
        try:
            with engine.connect() as db:
                cnt, _err, _fatal = self._count_with_connection(
                    db, conn.schema, table
                )
                return cnt
        except Exception as e:
            logger.warning("Count failed for %s.%s: %s", conn.schema, table, e)
            return None

    def _on_counts_ready(self, row: int, value: int) -> None:
        """Handle the asynchronous counts from the worker.

        Stores the count (cache), including -1 for failed counts, so the row
        is not re-enqueued and we only count each table once.

        Args:
            row: The model row index.
            value: Count value (negative means error) for current side.
        """
        # Validate row still present
        if row < 0 or row >= len(self._rows):
            return
        if self._side == "src":
            self._rows[row].cnt_src = value
        else:
            self._rows[row].cnt_dst = value
        # Remove from pending set so we no longer consider it "in flight"
        if hasattr(self, "_pending_lock"):
            with self._pending_lock:
                self._pending_set.discard(row)
        left = self.index(row, 1)
        right = self.index(row, 1)
        self.dataChanged.emit(left, right, [Qt.ItemDataRole.DisplayRole])

    # Queue helpers for single-threaded counting (cache: only count when
    # missing)
    def _enqueue_row(self, row: int) -> None:
        """Queue a row for counting if not already queued and not already
        cached.

        Does nothing when there is no connection for this side (e.g. no
        destination).

        Args:
            row: The row index to count.
        """
        if row < 0 or row >= len(self._rows):
            return
        conn_for_side = (
            self._src_conn if self._side == "src" else self._dst_conn
        )
        if conn_for_side is None:
            return
        # Do not enqueue if we already have a count (use cache)
        r = self._rows[row]
        if self._side == "src" and r.cnt_src is not None:
            return
        if self._side == "dst" and r.cnt_dst is not None:
            return
        if not hasattr(self, "_pending_lock"):
            self._pending_lock = threading.Lock()
            self._pending_rows = []
            self._pending_set = set()
        with self._pending_lock:
            if row not in self._pending_set:
                self._pending_rows.append(row)
                self._pending_set.add(row)

    def _dequeue_pending_row(self) -> Optional[int]:
        """Pop the next pending row or None if the queue is empty.

        Row stays in _pending_set until count is stored (in _on_counts_ready)
        so it cannot be re-enqueued by data() while the worker is counting.
        """
        if not hasattr(self, "_pending_lock"):
            return None

        with self._pending_lock:
            if not self._pending_rows:
                return None
            r = self._pending_rows.pop(0)
            # Do not remove from _pending_set here; remove in _on_counts_ready
            return r

    def _on_count_error(self, message: str) -> None:
        """Handle count worker error: emit count_failed and stop the worker."""
        self.count_failed.emit(message)
        self._stop_count_worker()

    def _ensure_worker(self) -> None:
        """Start the single count worker if it is not running and we have a
        connection.
        """
        conn_for_side = (
            self._src_conn if self._side == "src" else self._dst_conn
        )
        if conn_for_side is None:
            return
        w = getattr(self, "_worker", None)
        if w is None or not w.isRunning():
            self._worker = CountWorker(self)
            self._worker.counts_ready.connect(self._on_counts_ready)
            self._worker.count_error.connect(self._on_count_error)
            self._worker.start()

    def _stop_count_worker(self) -> None:
        """Stop the single count worker if it is running."""
        w = getattr(self, "_worker", None)
        if w is not None and w.isRunning():
            try:
                w.stop()
                w.wait(1000)
            except Exception as e:
                logger.error(
                    "TablesModel: failed to stop count worker: %s",
                    e,
                    exc_info=True,
                )
        self._worker = None

    def invalidate_counts(self) -> None:
        """Clear cached counts for this model side and requeue all rows."""
        for r in self._rows:
            if self._side == "src":
                r.cnt_src = None
            else:
                r.cnt_dst = None
        if not hasattr(self, "_pending_lock"):
            import threading as _th

            self._pending_lock = _th.Lock()
            self._pending_rows = []
            self._pending_set = set()
        with self._pending_lock:
            self._pending_rows = list(range(len(self._rows)))
            self._pending_set = set(self._pending_rows)
        self._ensure_worker()

    def _stop_all_count_workers(self) -> None:
        """Request stop for the single worker (compat shim)."""
        if hasattr(self, "_worker"):
            try:
                self._stop_count_worker()  # type: ignore[attr-defined]
            except Exception as e:
                logger.error(
                    "TablesModel: failed to stop all count workers: %s",
                    e,
                    exc_info=True,
                )
