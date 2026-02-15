"""Worker thread that inserts selected rows into the destination table."""

import logging
from typing import TYPE_CHECKING, Dict, List, Optional

from exdrf_al.connection import DbConn
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QWidget
from sqlalchemy import MetaData, Table, inspect

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)
VERBOSE = 1


class TransferRowsWorker(QThread):
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
    _dst: DbConn
    _table: str
    _rows: List[Dict[str, object]]
    _chunk: int

    def __init__(
        self,
        *,
        src_engine: "Engine",
        src_schema: Optional[str],
        dst: DbConn,
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
        except Exception as e:
            logger.log(
                VERBOSE,
                "TransferRowsWorker setObjectName: %s",
                e,
                exc_info=True,
            )

    def run(self) -> None:
        """Perform batched inserts and emit progress until done or canceled."""
        try:
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
            except Exception as emit_e:
                logger.error(
                    "Selected rows transfer failed: %s; emit error: %s",
                    e,
                    emit_e,
                    exc_info=True,
                )
