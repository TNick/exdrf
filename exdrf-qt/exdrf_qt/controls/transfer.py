import logging
import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple

from exdrf_al.connection import DbConn
from PyQt5.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QPoint,
    QSortFilterProxyModel,
    Qt,
    QThread,
    pyqtSignal,
)
from PyQt5.QtGui import QBrush, QColor, QFont, QIcon
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import (
    MetaData,
    Table,
    func,
    inspect,
    select,
)

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.filter_header import FilterHeader
from exdrf_qt.controls.seldb.choose_db import ChooseDb
from exdrf_qt.controls.table_viewer import (
    TableViewCtx,
    TableViewer,
    ViewerPlugin,
)

if TYPE_CHECKING:
    from typing import Callable

    from sqlalchemy.engine import Connection, Engine

    from exdrf_qt.context import QtContext


logger = logging.getLogger(__name__)
VERBOSE = 10


@dataclass(slots=True)
class _TblRow:
    """One entry in the tables list model.

    Attributes:
        name: The table name.
        cnt_src: Row count in the source connection; None until loaded.
        cnt_dst: Row count in the destination connection; None until loaded.
    """

    name: str
    cnt_src: Optional[int] = None
    cnt_dst: Optional[int] = None


class _CountWorker(QThread):
    """Single-threaded counter that serves one model sequentially.

    Emits counts_ready(row, value) as results become available.

    Attributes:
        _model: The model to serve.
        _stop: Whether to stop the worker.

    Signals:
        counts_ready: Emitted when a count is ready (row, value).
    """

    _model: "_TablesModel"
    _stop: bool

    counts_ready = pyqtSignal(int, int)
    count_error = pyqtSignal(str)

    def __init__(self, model: "_TablesModel") -> None:
        super().__init__(parent=model)
        self._model = model
        self._stop = False
        side = getattr(model, "_side", "?")
        self.setObjectName(f"TransferCountWorker-{side}")

    def stop(self) -> None:
        """Request the worker to stop."""
        self._stop = True

    def run(self) -> None:
        """Main worker loop. Uses a single DB connection for all counts."""
        try:
            threading.current_thread().name = self.objectName()
        except Exception:
            pass
        logger.log(VERBOSE, "CountWorker: started name=%s", self.objectName())
        conn = (
            self._model._src_conn
            if self._model._side == "src"
            else self._model._dst_conn
        )
        if conn is None:
            logger.log(
                VERBOSE,
                "CountWorker: no connection for side=%s, exiting",
                self._model._side,
            )
            return
        engine = conn.connect()
        db = engine.connect() if engine else None
        try:
            while not self._stop:
                row = self._model._dequeue_pending_row()
                if row is None:
                    time.sleep(0.05)
                    continue

                try:
                    tbl = self._model._rows[row].name
                except Exception as e:
                    logger.error(
                        "CountWorker: failed to get table name: %s",
                        e,
                        exc_info=True,
                    )
                    continue

                # Skip count if already cached; still emit so _on_counts_ready
                # clears _pending_set
                r = self._model._rows[row]
                if self._model._side == "src" and r.cnt_src is not None:
                    self.counts_ready.emit(row, r.cnt_src)
                    continue
                if self._model._side == "dst" and r.cnt_dst is not None:
                    self.counts_ready.emit(row, r.cnt_dst)
                    continue

                if db is not None:
                    (value, err_msg, is_fatal) = (
                        self._model._count_with_connection(db, conn.schema, tbl)
                    )
                    if err_msg is not None:
                        self.counts_ready.emit(row, -1)
                        if is_fatal:
                            # Abort counting for all tables; show error once per
                            # connection (e.g. permission denied for schema)
                            self.count_error.emit(err_msg)
                            self._stop = True
                            break
                        continue
                    value = value if value is not None else -1
                else:
                    value = -1
                if value >= 0:
                    logger.log(
                        VERBOSE, "CountWorker: count for %s = %s", tbl, value
                    )
                self.counts_ready.emit(row, int(value))
        finally:
            if db is not None:
                try:
                    db.close()
                except Exception as e:
                    logger.log(
                        1,
                        "CountWorker: error closing connection: %s",
                        e,
                        exc_info=True,
                    )
        logger.log(VERBOSE, "CountWorker: stopped name=%s", self.objectName())


class _NumericSortProxy(QSortFilterProxyModel):
    """Proxy that sorts numbers numerically when possible.

    Falls back to case-insensitive text sort when values are not numeric.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._filters: Dict[int, str] = {}
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setDynamicSortFilter(True)

    def set_filter(self, column: int, text: str) -> None:
        self._filters[column] = text or ""
        self.invalidateFilter()

    def filterAcceptsRow(
        self, source_row: int, source_parent: QModelIndex
    ) -> bool:  # noqa: N802
        model = self.sourceModel()
        if model is None:
            return True
        for col, pattern in self._filters.items():
            if not pattern:
                continue
            idx = model.index(source_row, col, source_parent)
            text = str(model.data(idx, Qt.ItemDataRole.DisplayRole) or "")
            if pattern.lower() not in text.lower():
                return False
        return True

    # type: ignore[override]
    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        model = self.sourceModel()
        if model is None:
            return super().lessThan(left, right)

        lv = model.data(left, Qt.ItemDataRole.DisplayRole)
        rv = model.data(right, Qt.ItemDataRole.DisplayRole)

        def _to_num(val):
            if val is None:
                return None
            s = str(val).strip()
            if not s:
                return None
            try:
                return int(s)
            except Exception:
                try:
                    return float(s)
                except Exception:
                    return None

        ln = _to_num(lv)
        rn = _to_num(rv)
        if ln is not None and rn is not None:
            return ln < rn
        ls = ("" if lv is None else str(lv)).lower()
        rs = ("" if rv is None else str(rv)).lower()
        return ls < rs


class _TablesModel(QAbstractTableModel, QtUseContext):
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
    _rows: List[_TblRow]
    _inflight: Dict[int, "_CountWorker"]

    _pending_lock: threading.Lock
    _pending_rows: List[int]
    _pending_set: Set[int]
    _worker: Optional["_CountWorker"]

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
        self._rows: List[_TblRow] = []
        self._inflight: Dict[int, _CountWorker] = {}

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
                self._rows.append(_TblRow(name=name))

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
                except Exception:
                    pass

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
        except Exception:
            pass
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
                    1,
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
            self._worker = _CountWorker(self)
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


class _TransferWorker(QThread):
    """Copy data from source tables to destination using SQLAlchemy Core.

    Attributes:
        table_started: Emitted when a table begins transfer with (table, total).
        progress: Emitted as rows are copied (table, done, total).
        table_done: Emitted when a table finishes (table, copied rows).
        error: Emitted when a table fails (table, error message).
        finished_all: Emitted when all tables finish or the worker stops.

    Private Attributes:
        _src: The source connection.
        _dst: The destination connection.
        _tables: List of table names to transfer.
        _chunk: Batch size for inserts.
    """

    # Private attributes
    _src: "DbConn"
    _dst: "DbConn"
    _tables: List[str]
    _chunk: int

    # table, total rows (may be 0 if unknown)
    table_started = pyqtSignal(str, int)
    progress = pyqtSignal(str, int, int)  # table, done, total
    table_done = pyqtSignal(str, int)
    error = pyqtSignal(str, str)
    finished_all = pyqtSignal()

    def __init__(
        self,
        *,
        src: DbConn,
        dst: DbConn,
        tables: List[str],
        chunk_size: int = 1000,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the worker.

        Args:
            src: The source connection.
            dst: The destination connection.
            tables: The list of table names to transfer.
            chunk_size: Insert batch size.
            parent: Optional Qt parent.
        """
        super().__init__(parent)
        self._src = src
        self._dst = dst
        self._tables = tables
        self._chunk = max(1, int(chunk_size))
        # Name the worker for easier diagnostics
        self.setObjectName("TransferTablesWorker")

    def run(self) -> None:  # noqa: D401
        """Thread entry: process each table sequentially and emit signals."""
        try:
            try:
                threading.current_thread().name = self.objectName()
            except Exception:
                pass
            src_engine = self._src.connect()
            dst_engine = self._dst.connect()
            assert src_engine is not None and dst_engine is not None
            logger.log(
                VERBOSE,
                "TransferWorker: starting run n_tables=%d",
                len(self._tables),
            )
            for tbl_name in self._tables:
                try:
                    copied = self._copy_table(src_engine, dst_engine, tbl_name)
                    self.table_done.emit(tbl_name, copied)
                except Exception as e:  # per-table isolation
                    logger.error(
                        "Transfer failed for table %s: %s",
                        tbl_name,
                        e,
                        exc_info=True,
                    )
                    self.error.emit(tbl_name, str(e))
                if self.isInterruptionRequested():
                    break
        finally:
            logger.log(VERBOSE, "TransferWorker: finished run")
            self.finished_all.emit()

    def _copy_table(
        self, src_engine: "Engine", dst_engine: "Engine", table: str
    ) -> int:
        """Copy one table from source to destination in chunks.

        Args:
            src_engine: The source SQLAlchemy engine.
            dst_engine: The destination SQLAlchemy engine.
            table: The table name to transfer.

        Returns:
            The number of rows copied.
        """
        src_meta = MetaData()
        dst_meta = MetaData()
        src_t = Table(
            table, src_meta, autoload_with=src_engine, schema=self._src.schema
        )

        # Ensure destination table exists; if not, create it based on source.
        dst_ins = inspect(dst_engine)
        if not dst_ins.has_table(table, schema=self._dst.schema):
            # Create compatible table in destination
            # Use tometadata to copy definition, adjusting schema
            try:
                # SQLAlchemy 1.4: tometadata
                new_t = src_t.tometadata(dst_meta, schema=self._dst.schema)
            except AttributeError:
                # Fallback for very old SA
                new_t = Table(
                    table,
                    dst_meta,
                    *[c.copy() for c in src_t.columns],
                    schema=self._dst.schema,
                )
            dst_meta.create_all(dst_engine, tables=[new_t])

        dst_t = Table(
            table,
            dst_meta,
            autoload_with=dst_engine,
            schema=self._dst.schema,
        )

        # Determine common columns
        dst_cols = {c.name for c in dst_t.columns}
        cols = [c for c in src_t.columns if c.name in dst_cols]

        # Determine total for progress (may be 0 if error)
        total_rows = 0
        try:
            with src_engine.connect() as s_conn:
                total_rows = int(
                    s_conn.scalar(select(func.count()).select_from(src_t)) or 0
                )
        except Exception:
            total_rows = 0
        logger.log(
            VERBOSE, "TransferWorker: table %s total_rows=%d", table, total_rows
        )
        self.table_started.emit(table, total_rows)

        total_copied = 0
        offset = 0
        with src_engine.connect() as s_conn, dst_engine.begin() as d_conn:
            while True:
                stmt = (
                    select(*cols)
                    .select_from(src_t)
                    .limit(self._chunk)
                    .offset(offset)
                )
                rows = list(s_conn.execute(stmt))
                if not rows:
                    break
                payload: List[Dict[str, object]] = []
                for r in rows:
                    m = r._mapping  # type: ignore[attr-defined]
                    payload.append({c.name: m[c.name] for c in cols})
                if payload:
                    d_conn.execute(dst_t.insert(), payload)
                total_copied += len(payload)
                offset += len(payload)
                self.progress.emit(table, total_copied, total_rows)
                if self.isInterruptionRequested():
                    break
        logger.log(
            VERBOSE, "TransferWorker: table %s copied=%d", table, total_copied
        )
        return total_copied


class _TransferSelectedPlugin(ViewerPlugin):
    """Viewer plugin that transfers selected rows to a destination connection.

    Private Attributes:
        _dst: Destination connection used by this plugin.
        _on_done: Optional callback to invoke when the transfer finishes.
        _chunk: Batch size for inserts.
        _active_worker: Currently running worker (if any).
        _dlg: The QProgressDialog used for progress UI (if any).
    """

    # Private attributes
    _dst: "DbConn"
    _on_done: Optional["Callable[[], None]"]
    _chunk: int
    _active_worker: Optional["_TransferRowsWorker"]
    _dlg: Optional["QProgressDialog"]

    def __init__(
        self,
        *,
        dst: "DbConn",
        on_done: Optional["Callable[[], None]"] = None,
        chunk: int = 500,
    ) -> None:
        """Initialize the plugin.

        Args:
            dst: Destination connection to insert selected rows into.
            on_done: Optional callback to notify completion.
            chunk: Batch size for insert.
        """
        self._dst = dst
        self._on_done = on_done
        self._chunk = max(1, int(chunk))
        self._active_worker: Optional[_TransferRowsWorker] = None
        self._dlg: Optional[QProgressDialog] = None

    def provide_actions(
        self, viewer: "TableViewer", ctx: TableViewCtx
    ) -> List[QAction]:
        """Produce context-menu actions for the given table view.

        Args:
            viewer: The host viewer instance.
            ctx: Context for the current tab/view.

        Returns:
            A list of actions; empty if not applicable.
        """
        sel = ctx.selected_records()
        if not sel:
            return []

        ac = QAction(
            viewer.t("tr.transfer.selected", "Transfer selected"), viewer
        )

        try:
            ac.setIcon(viewer.get_icon("layer_aspect_arrow"))
        except Exception as e:
            logger.error(
                "TransferSelectedPlugin: failed to set icon: %s",
                e,
                exc_info=True,
            )

        ac.triggered.connect(lambda: self._do_transfer(ctx))
        return [ac]

    def _do_transfer(self, ctx: TableViewCtx) -> None:
        """Kick off the selected-rows transfer with a progress dialog.

        Args:
            ctx: The view context holding selected rows and connection info.
        """
        rows = ctx.selected_records()
        if not rows:
            return

        worker = _TransferRowsWorker(
            src_engine=ctx.engine,
            src_schema=ctx.schema,
            dst=self._dst,
            table=ctx.table,
            rows=rows,
            chunk=self._chunk,
        )
        self._active_worker = worker
        # Progress dialog
        dlg = QProgressDialog(
            f"Transferring {ctx.table}...",
            "Cancel",
            0,
            len(rows),
            ctx.view,
        )
        self._dlg = dlg
        dlg.setWindowTitle("Transfer Selected")
        dlg.setAutoClose(True)
        dlg.setAutoReset(True)

        def _on_progress(done: int, total: int) -> None:
            """Update the dialog as batches complete.

            Args:
                done: Number of rows inserted so far.
                total: Total number of rows scheduled for transfer.
            """
            dlg.setMaximum(total)
            dlg.setValue(done)
            dlg.setLabelText(f"Transferring {ctx.table}... {done}/{total}")

        def _on_finished() -> None:
            """Handle worker completion and close the dialog."""
            dlg.setValue(dlg.maximum())
            dlg.close()
            if self._on_done:
                self._on_done()
            self._active_worker = None
            self._dlg = None

        def _on_canceled() -> None:
            """Cancel the running worker when the dialog is canceled."""
            worker.requestInterruption()

        worker.progress.connect(_on_progress)
        worker.finished.connect(_on_finished)
        dlg.canceled.connect(_on_canceled)
        worker.start()

    def on_view_created(self, viewer: "TableViewer", ctx: TableViewCtx) -> None:
        """Ensure cleanup if the hosting viewer is destroyed.

        Args:
            viewer: The hosting viewer widget.
            ctx: The created view context (unused).
        """
        try:
            viewer.destroyed.connect(lambda *_: self._cancel_active_worker())
        except Exception as e:
            logger.error(
                "TransferSelectedPlugin: failed to connect destroyed "
                "signal: %s",
                e,
                exc_info=True,
            )

    def _cancel_active_worker(self) -> None:
        """Cancel and wait for the active worker, if any."""
        try:
            if self._active_worker and self._active_worker.isRunning():
                self._active_worker.requestInterruption()
                self._active_worker.wait(2000)
        except Exception as e:
            logger.error(
                "TransferSelectedPlugin: failed to cancel active worker: %s",
                e,
                exc_info=True,
            )


class _TransferRowsWorker(QThread):
    """Worker that inserts a list of provided rows into the destination table.

    Attributes:
        progress: Emitted after each batch with (done, total).
        error: Emitted on failure with the error message.

    Private Attributes:
        _src_engine: The source engine (used for reflection only).
        _src_schema: The source schema name or None.
        _dst: Destination connection for inserts.
        _table: Target table name.
        _rows: Rows to insert (list of dicts).
        _chunk: Batch size for inserts.
    """

    # Public attributes (signals)
    progress: pyqtSignal = pyqtSignal(int, int)
    error: pyqtSignal = pyqtSignal(str)

    # Private attributes
    _src_engine: "Engine"
    _src_schema: Optional[str]
    _dst: "DbConn"
    _table: str
    _rows: List[Dict[str, object]]
    _chunk: int

    def __init__(
        self,
        *,
        src_engine: "Engine",
        src_schema: Optional[str],
        dst: "DbConn",
        table: str,
        rows: List[Dict[str, object]],
        chunk: int = 500,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the worker for selected rows.

        Args:
            src_engine: Source SQLAlchemy engine (for reflection only).
            src_schema: Optional source schema.
            dst: Destination connection.
            table: Destination table name.
            rows: Rows to insert (list of dicts).
            chunk: Batch size for insert.
            parent: Optional Qt parent widget.
        """
        super().__init__(parent)
        self._src_engine = src_engine
        self._src_schema = src_schema
        self._dst = dst
        self._table = table
        self._rows = rows
        self._chunk = max(1, int(chunk))
        # Name thread for diagnostics
        try:
            safe_table = (table or "").replace(" ", "_")
            self.setObjectName(f"TransferRowsWorker-{safe_table}")
        except Exception:
            pass

    def run(self) -> None:
        """Perform batched inserts and emit progress until done or canceled."""
        try:
            try:
                threading.current_thread().name = self.objectName()
            except Exception as e:
                logger.error(
                    "TransferRowsWorker: failed to set thread name: %s",
                    e,
                    exc_info=True,
                )

            dst_engine = self._dst.connect()
            src_meta = MetaData()
            dst_meta = MetaData()
            src_t = Table(
                self._table,
                src_meta,
                autoload_with=self._src_engine,
                schema=self._src_schema,
            )
            # Ensure destination table exists
            ins = inspect(dst_engine)
            if not ins.has_table(self._table, schema=self._dst.schema):
                try:
                    new_t = src_t.tometadata(dst_meta, schema=self._dst.schema)
                except AttributeError:
                    new_t = Table(
                        self._table,
                        dst_meta,
                        *[c.copy() for c in src_t.columns],
                        schema=self._dst.schema,
                    )
                dst_meta.create_all(dst_engine, tables=[new_t])

            dst_t = Table(
                self._table,
                dst_meta,
                autoload_with=dst_engine,
                schema=self._dst.schema,
            )

            # Only insert columns present in destination
            allowed = {c.name for c in dst_t.columns}
            payload = [
                {k: v for k, v in r.items() if k in allowed} for r in self._rows
            ]
            total = len(payload)
            done = 0
            if total:
                with dst_engine.begin() as conn:
                    for i in range(0, total, self._chunk):
                        if self.isInterruptionRequested():
                            break
                        batch = payload[i : i + self._chunk]
                        conn.execute(dst_t.insert(), batch)
                        done += len(batch)
                        self.progress.emit(done, total)
        except Exception as e:
            logger.error("Selected rows transfer failed: %s", e, exc_info=True)
            try:
                self.error.emit(str(e))
            except Exception:
                logger.error(
                    "Selected rows transfer failed: %s", e, exc_info=True
                )


class TransferWidget(QWidget, QtUseContext):
    """Widget to transfer data from one DB connection to another.

    Layout: two panes (source on left, destination on right). Each pane has a
    database chooser and a lazy-count tables list. Right-click on the source
    list enables full-table Transfer and View; both panes support View via a
    reusable TableViewer. Selected-row transfers are available inside the
    viewer via a plugin.

    Attributes:
        ctx: The application context.

    Private Attributes:
        _src_conn: Current source connection.
        _dst_conn: Current destination connection.
        _src_view_win: Source TableViewer window if open.
        _dst_view_win: Destination TableViewer window if open.
        _spin_chunk: Spin control holding the current chunk size.
        _src_db: Source DB chooser.
        _dst_db: Destination DB chooser.
        _src_model: Source tables model.
        _dst_model: Destination tables model.
        _src_view: Source tables view.
        _dst_view: Destination tables view.
    """

    # Public attributes
    ctx: "QtContext"

    # Private attributes
    _src_conn: Optional["DbConn"]
    _dst_conn: Optional["DbConn"]
    _src_view_win: Optional[TableViewer]
    _dst_view_win: Optional[TableViewer]
    _spin_chunk: "QSpinBox"
    _src_db: "ChooseDb"
    _dst_db: "ChooseDb"
    _btn_settings: "QPushButton"
    _btn_bootstrap: "QPushButton"
    _src_model: _TablesModel
    _dst_model: _TablesModel
    _src_view: "QTableView"
    _dst_view: "QTableView"
    _full_worker: Optional["_TransferWorker"]
    _sync_scroll: bool
    _sync_in_progress: bool

    def __init__(self, ctx, parent: Optional["QWidget"] = None) -> None:
        """Initialize the transfer widget.

        Args:
            ctx: The application context.
            parent: Optional Qt parent widget.
        """
        super().__init__(parent)
        self.ctx = ctx

        # Connections for both sides
        self._src_conn: Optional[DbConn] = None
        self._dst_conn: Optional[DbConn] = None

        # One count-error toast per connection selection (cleared when
        # selection changes)
        self._src_count_error_shown: bool = False
        self._dst_count_error_shown: bool = False

        # External viewer windows (owned by MDI or top-level)
        self._src_view_win: Optional[TableViewer] = None
        self._dst_view_win: Optional[TableViewer] = None

        # Build UI controls and top toolbar
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(2, 2, 2, 2)
        top_bar.setSpacing(6)
        lbl_chunk = QLabel(self.t("tr.chunk", "Transfer chunk size:"), self)
        self._spin_chunk = QSpinBox(self)
        self._spin_chunk.setRange(1, 50000)
        self._spin_chunk.setSingleStep(100)
        self._spin_chunk.setValue(1000)
        top_bar.addWidget(lbl_chunk)
        top_bar.addWidget(self._spin_chunk)

        # Settings button opens the DB manager dialog
        self._btn_settings = QPushButton(
            self.t("tr.settings", "Settings"), self
        )
        self._btn_settings.setIcon(self.get_icon("edit_button"))
        self._btn_settings.clicked.connect(self._on_open_settings)

        # Bootstrap button applies to the destination connection
        self._btn_bootstrap = QPushButton(
            self.t("tr.bootstrap", "Bootstrap"), self
        )
        self._btn_bootstrap.setIcon(self.get_icon("sitemap_application_blue"))
        self._btn_bootstrap.clicked.connect(self._on_bootstrap_dst)

        top_bar.addWidget(self._btn_settings)
        top_bar.addWidget(self._btn_bootstrap)
        top_bar.addStretch(1)

        # Create the two-pane splitter
        split = QSplitter(Qt.Orientation.Horizontal, self)
        l_side = self._build_side(is_src=True)
        r_side = self._build_side(is_src=False)
        split.addWidget(l_side)
        split.addWidget(r_side)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 1)

        # Compose the root layout
        root = QVBoxLayout(self)
        root.setContentsMargins(2, 2, 2, 2)
        root.addLayout(top_bar)
        root.addWidget(split)
        self.setLayout(root)
        logger.log(VERBOSE, "TransferWidget: UI initialized")

        # Populate database choosers
        self._src_db.populate_db_connections()
        self._dst_db.populate_db_connections()

        # Select newest connection for source on startup, clear destination
        self._select_newest_for_source()
        self._clear_destination()

        # Initial refresh
        self._src_model.refresh()
        self._dst_model.refresh()

        # Track running full-table transfer worker (if any)
        self._full_worker = None
        logger.log(VERBOSE, "TransferWidget: initial state ready")

        # Sync scroll (disabled by default)
        self._sync_scroll = False
        self._sync_in_progress = False

    # UI construction helpers
    def _build_side(self, *, is_src: bool) -> QWidget:
        """Construct one side of the UI (source or destination).

        Args:
            is_src: True for the source pane, False for destination.

        Returns:
            The constructed side widget.
        """
        w = QWidget(self)
        ly = QVBoxLayout(w)
        ly.setContentsMargins(2, 2, 2, 2)
        ly.setSpacing(4)

        db = ChooseDb(ctx=self.ctx, parent=w)
        db.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        ly.addWidget(db)

        model = _TablesModel(ctx=self.ctx, side="src" if is_src else "dst")
        view = QTableView(w)
        proxy = _NumericSortProxy(view)
        proxy.setSourceModel(model)
        proxy.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        proxy.setDynamicSortFilter(True)
        view.setModel(proxy)
        view.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        # Install per-column filter header
        header = FilterHeader(ctx=self.ctx, parent=view)
        view.setHorizontalHeader(header)
        header.init_filters(
            headers=[
                self.t("tr.tables.name", "Table"),
                self.t("tr.tables.counts", "Rows"),
            ],
            on_text_changed=lambda c, t: proxy.set_filter(c, t),
        )
        try:
            header.setSortIndicatorShown(True)
            header.setSectionsClickable(True)
        except Exception:
            pass
        view.setSortingEnabled(True)
        view.setSelectionBehavior(QAbstractItemView.SelectRows)
        view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        view.setAlternatingRowColors(True)
        view.setSortingEnabled(True)
        view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        view.customContextMenuRequested.connect(
            lambda p, s=self, v=view, src=is_src: s._show_ctx_menu(v, p, src)
        )
        vh = view.verticalHeader()
        if vh is not None:
            vh.setVisible(False)
        hh = view.horizontalHeader()
        if hh is not None:
            hh.setStretchLastSection(True)
        ly.addWidget(view)

        if is_src:
            self._src_db = db
            self._src_model = model
            self._src_view = view
            model.count_failed.connect(
                lambda msg: self._on_count_failed(msg, is_src=True)
            )
            db.currentIndexChanged.connect(
                lambda *_: self._apply_src_selection()
            )
        else:
            self._dst_db = db
            self._dst_model = model
            self._dst_view = view
            model.count_failed.connect(
                lambda msg: self._on_count_failed(msg, is_src=False)
            )
            db.currentIndexChanged.connect(
                lambda *_: self._apply_dst_selection()
            )

        # If both views exist and sync was enabled previously, apply now
        try:
            if (
                getattr(self, "_src_view", None) is not None
                and getattr(self, "_dst_view", None) is not None
            ):
                self._apply_sync_scroll_connections()
        except Exception:
            pass

        return w

    # Selection -> connections
    def _apply_src_selection(self) -> None:
        """Update source connection based on the chooser selection.

        Also enforces that destination is different; if same, clears dest.
        """
        logger.log(VERBOSE, "TransferWidget: applying src selection")
        self._src_count_error_shown = False

        cfg = self._current_cfg(self._src_db)
        if not cfg:
            self._src_conn = None
        else:
            self._src_conn = DbConn(
                c_string=cfg.get("c_string", ""),
                schema=cfg.get("schema", "public") or "public",
            )
        # Enforce different connections: if equal, clear destination
        if self._is_same_conn(self._src_conn, self._dst_conn):
            self._clear_destination()
        self._src_model.set_connections(self._src_conn, self._dst_conn)
        self._src_model.refresh()
        logger.log(
            VERBOSE,
            "TransferWidget: applied src selection %s",
            None if not cfg else cfg.get("id"),
        )

    def _apply_dst_selection(self) -> None:
        """Update destination connection based on the chooser selection.

        Enforces different source/destination by clearing destination if same.
        """
        logger.log(VERBOSE, "TransferWidget: applying dst selection")
        self._dst_count_error_shown = False

        cfg = self._current_cfg(self._dst_db)
        if not cfg:
            self._dst_conn = None
        else:
            self._dst_conn = DbConn(
                c_string=cfg.get("c_string", ""),
                schema=cfg.get("schema", "public") or "public",
            )
        # If same as source keep source and clear destination
        if self._is_same_conn(self._src_conn, self._dst_conn):
            self._clear_destination()
        # Update only destination-side model and refresh it
        try:
            # Always map (source, destination)
            self._dst_model.set_connections(self._src_conn, self._dst_conn)
            self._dst_model.refresh()
        except Exception as e:
            logger.error(
                "TransferWidget: failed to refresh destination after "
                "selection: %s",
                e,
                exc_info=True,
            )
        logger.log(
            VERBOSE,
            "TransferWidget: applied dst selection %s",
            None if not cfg else cfg.get("id"),
        )

    def _current_cfg(self, db: ChooseDb) -> Optional[dict]:
        """Extract the selected DB configuration dict from a ChooseDb.

        Args:
            db: The chooser to read from.

        Returns:
            The configuration dict or None if none selected.
        """
        idx = db.currentIndex()
        model = db.model()
        try:
            # DbConfigModel API
            from exdrf_qt.controls.seldb.db_config_model import DbConfigModel

            if isinstance(model, DbConfigModel):
                mi = model.index(idx, 0)
                return model.get_config(mi)
        except Exception:
            pass
        return None

    # Utilities enforcing different connections and selection of newest
    def _current_config_id(self, chooser: "ChooseDb") -> Optional[str]:
        """Return the currently selected configuration id for a chooser.

        Args:
            chooser: The database chooser.

        Returns:
            The selected configuration id or None.
        """
        try:
            from exdrf_qt.controls.seldb.db_config_model import DbConfigModel

            model = chooser.model()
            if not isinstance(model, DbConfigModel):
                return None
            idx = chooser.currentIndex()
            if idx < 0:
                return None
            cfg = model.get_config(model.index(idx, 0))
            if cfg:
                return cfg.get("id")
        except Exception:
            pass
        return None

    def _set_selection_by_id(
        self, chooser: "ChooseDb", cfg_id: Optional[str]
    ) -> bool:
        """Try to select a config by id in the provided chooser.

        Args:
            chooser: The database chooser to alter.
            cfg_id: The configuration id to select.

        Returns:
            True if the selection was changed to the id, False otherwise.
        """
        if not cfg_id:
            return False
        try:
            from exdrf_qt.controls.seldb.db_config_model import DbConfigModel

            model = chooser.model()
            if not isinstance(model, DbConfigModel):
                return False
            idx = model.find_config_index(cfg_id)
            if idx is not None:
                chooser.setCurrentIndex(idx.row())
                return True
        except Exception:
            pass
        return False

    def _is_same_conn(
        self, a: Optional["DbConn"], b: Optional["DbConn"]
    ) -> bool:
        """Compare two connections by connection string and schema.

        Args:
            a: First connection.
            b: Second connection.

        Returns:
            True if both are non-None and have identical c_string and schema.
        """
        if a is None or b is None:
            return False
        return a.c_string == b.c_string and a.schema == b.schema

    def _clear_destination(self) -> None:
        """Clear the destination selection and connection."""
        self._dst_conn = None
        try:
            self._dst_db.setCurrentIndex(-1)
        except Exception as e:
            logger.error(
                "TransferWidget: failed to clear destination: %s",
                e,
                exc_info=True,
            )

        self._src_model.set_connections(self._src_conn, self._dst_conn)
        self._dst_model.set_connections(self._src_conn, self._dst_conn)
        self._dst_model.refresh()

    def _select_newest_for_source(self) -> None:
        """Select the newest connection for the source chooser.

        Newest is determined by created_at if available, otherwise by
        the order in settings (last entry wins).
        """
        try:
            from exdrf_qt.controls.seldb.db_config_model import DbConfigModel

            model = self._src_db.model()
            if not isinstance(model, DbConfigModel):
                return

            configs = self.ctx.stg.get_db_configs()
            newest = None
            if configs:
                # Pick by max created_at if present, else last item
                def _key(c):
                    return c.get("created_at") or ""

                with_created = [c for c in configs if c.get("created_at")]
                if with_created:
                    newest = max(with_created, key=_key)
                else:
                    newest = configs[-1]
            if newest and newest.get("id"):
                idx = model.find_config_index(newest["id"])  # type: ignore
                if idx is not None:
                    self._src_db.setCurrentIndex(idx.row())
                    logger.log(
                        VERBOSE,
                        "TransferWidget: newest source id=%s",
                        newest["id"],
                    )
        except Exception as e:
            logger.error(
                "Failed to select newest for source: %s", e, exc_info=True
            )

    # Settings and bootstrap actions
    def _on_open_settings(self) -> None:
        """Open the database settings dialog and refresh the choosers after.

        Attempts to preserve current selections; if a selection disappears,
        falls back to newest on source and clears destination.
        """
        prev_src_id = None
        prev_dst_id = None
        try:
            from exdrf_qt.controls.seldb.sel_db import SelectDatabaseDlg

            # Preserve current selections
            prev_src_id = self._current_config_id(self._src_db)
            prev_dst_id = self._current_config_id(self._dst_db)

            dlg = SelectDatabaseDlg(
                ctx=self.ctx, parent=self, show_transfer_button=False
            )
            dlg.exec_()
        except Exception as e:
            logger.error("Failed to open settings dialog: %s", e, exc_info=True)
        finally:
            # Refresh both choosers to reflect any changes
            try:
                self._src_db.populate_db_connections()
                self._dst_db.populate_db_connections()

                # Try to restore previous selections
                restored_src = self._set_selection_by_id(
                    self._src_db, prev_src_id
                )
                restored_dst = self._set_selection_by_id(
                    self._dst_db, prev_dst_id
                )

                if not restored_src:
                    # Fallback to newest + empty
                    self._select_newest_for_source()
                if not restored_dst:
                    self._clear_destination()

                # Apply effects (update connections and models)
                self._apply_src_selection()
                self._apply_dst_selection()
                logger.log(
                    VERBOSE,
                    "TransferWidget: settings closed, restored src=%s dst=%s",
                    prev_src_id,
                    prev_dst_id,
                )
            except Exception as e:
                logger.error(
                    "Failed to restore selections: %s", e, exc_info=True
                )

    def _on_bootstrap_dst(self) -> None:
        """Run bootstrap on the selected destination connection."""
        cfg = self._current_cfg(self._dst_db)
        if not cfg:
            QMessageBox.information(
                self,
                self.t("cmn.info", "Info"),
                self.t("tr.no-dst", "No destination connection selected."),
            )
            return

        # Confirm with the user before proceeding
        conn_name = cfg.get("name") or cfg.get("c_string", "")
        question = self.t(
            "tr.bootstrap.confirm",
            "Bootstrap the destination database '{name}'?\nProceed?",
            name=conn_name,
        )
        reply = QMessageBox.question(
            self,
            self.t("cmn.question", "Question"),
            question,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # Build a temporary context to bootstrap this DB
        try:
            local_ctx = self.ctx.__class__(  # type: ignore
                c_string=cfg.get("c_string", ""),
                schema=cfg.get("schema", "public") or "public",
                top_widget=self.ctx.top_widget,
                work_relay=None,
                asset_sources=self.ctx.asset_sources,
                auto_migrate=False,
            )
            try:
                local_ctx.connect()
            except Exception as e:
                self.ctx.show_error(
                    title=self.ctx.t("cmn.error", "Error"),
                    message=self.ctx.t(
                        "cmn.db.err-connect",
                        "Failed to connect to the database using {cons}: {err}",
                        cons=local_ctx.c_string,
                        err=str(e),
                    ),
                )
                return
            try:
                if not local_ctx.bootstrap():
                    return
            except Exception as e:
                self.ctx.show_error(
                    title=self.ctx.t("cmn.error", "Error"),
                    message=self.ctx.t(
                        "cmn.db.err-bootstrap",
                        "Failed to bootstrap the database: {err}",
                        err=str(e),
                    ),
                )
                return
            QMessageBox.information(
                self,
                self.t("cmn.info", "Info"),
                self.t("cmn.db.bootstrap-success", "Bootstrap successful!"),
            )
        except Exception as e:
            logger.error("Bootstrap failed: %s", e, exc_info=True)

    # Context menu
    def _show_ctx_menu(
        self, view: QTableView, point: QPoint, is_src: bool
    ) -> None:
        """Show a context menu appropriate for the given table view.

        Args:
            view: The view that was right-clicked.
            point: Local position for the menu.
            is_src: Whether the menu is for the source pane.
        """
        menu = QMenu(view)
        act_view = QAction(self.t("tr.view", "View"), menu)
        act_view.triggered.connect(lambda: self._on_view_tables(view, is_src))
        menu.addAction(act_view)

        if is_src:
            act_transfer = QAction(self.t("tr.transfer", "Transfer"), menu)
            icon: Optional[QIcon]
            try:
                icon = self.get_icon("layer_aspect_arrow")
                act_transfer.setIcon(icon)
            except Exception:
                logger.error(
                    "Failed to get icon for transfer action", exc_info=True
                )
            act_transfer.triggered.connect(lambda: self._on_transfer(view))
            menu.addSeparator()
            menu.addAction(act_transfer)

        # Sync scroll toggle (check-mark reflects current state)
        act_sync = QAction(self.t("tr.sync.scroll", "Sync Scroll"), menu)
        act_sync.setCheckable(True)
        act_sync.setChecked(self._sync_scroll)
        act_sync.toggled.connect(self._set_sync_scroll)
        menu.addAction(act_sync)

        act_refresh = QAction(self.t("tr.refresh", "Refresh Counts"), menu)
        act_refresh.triggered.connect(lambda: self._on_refresh_counts(view))
        menu.addSeparator()
        menu.addAction(act_refresh)

        vp = view.viewport()
        if vp is None:
            return
        menu.exec_(vp.mapToGlobal(point))

    def _on_refresh_counts(self, view: QTableView) -> None:
        """Refresh counts for the given view's model."""
        model = view.model()
        if isinstance(model, _TablesModel):
            model.invalidate_counts()

    # Actions
    def _selected_tables(
        self, view: QTableView, model: _TablesModel
    ) -> List[str]:
        """Return table names corresponding to the current selection.

        Args:
            view: The view to read the selection from.
            model: The backing list model.

        Returns:
            A list of selected table names.
        """
        sel = view.selectionModel()
        if not sel:
            return []
        indexes = sel.selectedRows(0)
        out: List[str] = []
        proxy_model = view.model()
        # Resolve the source model to access table_name()
        try:
            source_model = (
                proxy_model.sourceModel()  # type: ignore[attr-defined]
                if isinstance(proxy_model, QSortFilterProxyModel)
                else model
            )
        except Exception:
            source_model = model

        for idx in indexes:
            try:
                if isinstance(proxy_model, QSortFilterProxyModel):
                    src_idx = proxy_model.mapToSource(idx)
                    r = src_idx.row()
                else:
                    r = idx.row()
            except Exception:
                r = idx.row()
            # Lookup table name in the source model
            name = source_model.table_name(r)  # type: ignore[attr-defined]
            if name:
                out.append(name)
        return out

    def _on_view_tables(self, view: QTableView, is_src: bool) -> None:
        """Open the table viewer for selected tables on the proper connection.

        Args:
            view: The originating list view.
            is_src: True if viewing from the source pane.
        """
        model: _TablesModel = view.model()  # type: ignore[assignment]
        tables = self._selected_tables(view, model)
        if not tables:
            return
        conn = self._src_conn if is_src else self._dst_conn
        if conn is None or conn.engine is None:
            try:
                engine = conn.connect() if conn else None
            except Exception:
                engine = None
        else:
            engine = conn.engine
        if engine is None:
            return

        win = self._src_view_win if is_src else self._dst_view_win
        if win is None:
            win = TableViewer(ctx=self.ctx)
            # Install plugin to transfer selected rows when viewing the source
            if is_src and self._dst_conn is not None:
                win.add_plugin(
                    _TransferSelectedPlugin(
                        dst=self._dst_conn,
                        on_done=self._refresh_counts,
                        chunk=self._spin_chunk.value(),
                    )
                )
            win.destroyed.connect(
                lambda *_: self._on_viewer_closed(is_src=is_src)
            )
            title = (
                self.t("tr.src.viewer", "Source Tables")
                if is_src
                else self.t("tr.dst.viewer", "Destination Tables")
            )
            if (
                hasattr(self.ctx, "create_window")
                and self.ctx.top_widget is not None
            ):
                self.ctx.create_window(win, title)
            else:
                win.setWindowTitle(title)
                win.resize(900, 600)
                win.show()
            if is_src:
                self._src_view_win = win
            else:
                self._dst_view_win = win

        for t in tables:
            try:
                win.open_table(
                    engine=engine,
                    schema=conn.schema if conn else None,
                    table=t,
                )
            except Exception as e:
                logger.error("Failed to open table %s: %s", t, e, exc_info=True)

    def _on_viewer_closed(self, *, is_src: bool) -> None:
        """Clear viewer references when a viewer window is closed.

        Args:
            is_src: Which viewer was closed (source or destination).
        """
        if is_src:
            self._src_view_win = None
        else:
            self._dst_view_win = None

    def _on_transfer(self, view: QTableView) -> None:
        """Start a whole-table transfer for selected tables.

        Args:
            view: The source tables view.
        """
        tables = self._selected_tables(view, self._src_model)
        if not tables or not self._src_conn or not self._dst_conn:
            return
        worker = _TransferWorker(
            src=self._src_conn,
            dst=self._dst_conn,
            tables=tables,
            chunk_size=self._spin_chunk.value(),
        )
        worker.error.connect(self._on_transfer_error)
        # Keep a reference so thread is not destroyed while running
        self._full_worker = worker
        logger.log(
            VERBOSE,
            "TransferWidget: start full transfer tables=%s chunk=%d",
            tables,
            self._spin_chunk.value(),
        )
        # Progress UI
        dlg = QProgressDialog(
            self.t("tr.transfer", "Transfer"),
            self.t("cmn.cancel", "Cancel"),
            0,
            0,
            self,
        )
        dlg.setWindowTitle(self.t("tr.transfer", "Transfer"))
        dlg.setAutoReset(True)
        dlg.setAutoClose(True)

        def _on_started(tbl: str, total: int) -> None:
            """Initialize the dialog range/label for the current table.

            Args:
                tbl: Current table name.
                total: Total rows to copy (0 if unknown).
            """
            if total > 0:
                dlg.setRange(0, total)
            else:
                dlg.setRange(0, 0)  # busy
            dlg.setValue(0)
            dlg.setLabelText(
                self.t(
                    "tr.transfer.table",
                    "Transferring {tbl}...",
                    tbl=tbl,
                )
            )

        def _on_progress(tbl: str, done: int, total: int) -> None:
            """Update dialog as rows are copied.

            Args:
                tbl: Current table name.
                done: Rows copied so far.
                total: Total rows in table (0 if unknown).
            """
            if total > 0:
                if dlg.maximum() != total:
                    dlg.setRange(0, total)
                dlg.setValue(done)
            dlg.setLabelText(
                self.t(
                    "tr.transfer.progress",
                    "Transferring {tbl}... {done}/{total}",
                    tbl=tbl,
                    done=done,
                    total=total,
                )
            )

        def _on_finished() -> None:
            """Refresh counts and close the dialog on completion."""
            dlg.setValue(dlg.maximum())
            dlg.close()
            self._refresh_counts()
            logger.log(VERBOSE, "TransferWidget: full transfer finished")

        def _on_canceled() -> None:
            """Cancel the running worker."""
            worker.requestInterruption()

        worker.table_started.connect(_on_started)
        worker.progress.connect(_on_progress)
        worker.finished_all.connect(_on_finished)
        worker.finished_all.connect(lambda: setattr(self, "_full_worker", None))
        dlg.canceled.connect(_on_canceled)
        worker.start()

    def _refresh_counts(self) -> None:
        self._src_model.refresh()
        self._dst_model.refresh()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Stop background threads before closing the widget."""
        try:
            if self._full_worker and self._full_worker.isRunning():
                self._full_worker.requestInterruption()
                self._full_worker.wait(2000)
        except Exception:
            pass
        try:
            self._src_model._stop_all_count_workers()
            self._dst_model._stop_all_count_workers()
        except Exception:
            pass
        # Disconnect sync scroll
        try:
            self._disconnect_sync_scroll()
        except Exception:
            pass
        super().closeEvent(event)

    # -------------------------------
    # Sync scroll helpers
    # -------------------------------
    def _toggle_sync_scroll(self) -> None:
        """Toggle sync scroll (legacy helper)."""
        self._set_sync_scroll(not self._sync_scroll)

    def _set_sync_scroll(self, enabled: bool) -> None:
        """Set sync scroll state and (dis)connect listeners accordingly.

        Args:
            enabled: Whether to enable synchronized scrolling.
        """
        self._sync_scroll = bool(enabled)
        self._apply_sync_scroll_connections()

    def _apply_sync_scroll_connections(self) -> None:
        """Connect or disconnect scrollbars based on current sync state."""
        self._disconnect_sync_scroll()
        if not self._sync_scroll:
            return
        if (
            getattr(self, "_src_view", None) is None
            or getattr(self, "_dst_view", None) is None
        ):
            return
        sv = self._src_view.verticalScrollBar()
        dv = self._dst_view.verticalScrollBar()
        try:
            sv.valueChanged.connect(self._on_src_scroll)
        except Exception:
            pass
        try:
            dv.valueChanged.connect(self._on_dst_scroll)
        except Exception:
            pass

    def _disconnect_sync_scroll(self) -> None:
        """Disconnect any existing sync scroll connections."""
        try:
            if getattr(self, "_src_view", None) is not None:
                sv = self._src_view.verticalScrollBar()
                sv.valueChanged.disconnect(self._on_src_scroll)
        except Exception:
            pass
        try:
            if getattr(self, "_dst_view", None) is not None:
                dv = self._dst_view.verticalScrollBar()
                dv.valueChanged.disconnect(self._on_dst_scroll)
        except Exception:
            pass

    def _on_src_scroll(self, value: int) -> None:
        """Propagate source scroll to destination when sync is enabled.

        Avoid recursive updates by using an in-progress guard and map the
        scroll value proportionally when maximums differ.
        """
        if (
            not self._sync_scroll
            or self._sync_in_progress
            or getattr(self, "_dst_view", None) is None
        ):
            return
        dv = self._dst_view.verticalScrollBar()
        sv = self._src_view.verticalScrollBar()
        try:
            self._sync_in_progress = True
            src_max = max(1, sv.maximum())
            dst_max = dv.maximum()
            mapped = int(
                round(min(max(0, value), src_max) * (dst_max / src_max))
            )
            dv.setValue(mapped)
        finally:
            self._sync_in_progress = False

    def _on_dst_scroll(self, value: int) -> None:
        """Propagate destination scroll to source when sync is enabled.

        Avoid recursive updates by using an in-progress guard and map the
        scroll value proportionally when maximums differ.
        """
        if (
            not self._sync_scroll
            or self._sync_in_progress
            or getattr(self, "_src_view", None) is None
        ):
            return
        sv = self._src_view.verticalScrollBar()
        dv = self._dst_view.verticalScrollBar()
        try:
            self._sync_in_progress = True
            dst_max = max(1, dv.maximum())
            src_max = sv.maximum()
            mapped = int(
                round(min(max(0, value), dst_max) * (src_max / dst_max))
            )
            sv.setValue(mapped)
        finally:
            self._sync_in_progress = False

    def _on_count_failed(self, message: str, is_src: bool) -> None:
        """Show count error toast once per connection selection.

        Args:
            message: Error message from the count worker.
            is_src: True for source side, False for destination.
        """
        if is_src and self._src_count_error_shown:
            return
        if not is_src and self._dst_count_error_shown:
            return
        from exdrf_qt.controls.toast import Toast

        Toast.show_error(self, message)
        if is_src:
            self._src_count_error_shown = True
        else:
            self._dst_count_error_shown = True

    def _on_transfer_error(self, table_name: str, message: str) -> None:
        """Handle transfer errors by showing the failure reason in a toast.

        Args:
            table_name: The table that failed to transfer.
            message: The exception or error message (reason for failure).
        """
        from exdrf_qt.controls.toast import Toast

        Toast.show_error(
            self,
            "%s: %s" % (table_name, message),
        )
