"""Worker thread that copies full tables from source to destination."""

import logging
from typing import TYPE_CHECKING, Dict, List, Optional

from exdrf_al.connection import DbConn
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget
from sqlalchemy import MetaData, Table, func, inspect, select

from exdrf_qt.utils.native_threads import PythonThread

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)
VERBOSE = 1


class TransferWorker(PythonThread):
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
    _src: DbConn
    _dst: DbConn
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
            except AttributeError as e:
                # Fallback for very old SA
                logger.log(
                    VERBOSE,
                    "tometadata not available, using column copy: %s",
                    e,
                    exc_info=True,
                )
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
        except Exception as e:
            logger.log(
                VERBOSE,
                "TransferWorker: could not get total for %s: %s",
                table,
                e,
                exc_info=True,
            )
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
