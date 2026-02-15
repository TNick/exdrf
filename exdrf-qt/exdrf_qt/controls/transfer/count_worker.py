"""Worker thread that computes table row counts for the tables model."""

import logging
import time
from typing import TYPE_CHECKING

from PyQt5.QtCore import QThread, pyqtSignal

if TYPE_CHECKING:
    from exdrf_qt.controls.transfer.tables_model import TablesModel

logger = logging.getLogger(__name__)
VERBOSE = 1


class CountWorker(QThread):
    """Single-threaded counter that serves one model sequentially.

    Emits counts_ready(row, value) as results become available.

    Attributes:
        _model: The model to serve.
        _stop: Whether to stop the worker.

    Signals:
        counts_ready: Emitted when a count is ready (row, value).
    """

    _model: "TablesModel"
    _stop: bool

    counts_ready = pyqtSignal(int, int)
    count_error = pyqtSignal(str)

    def __init__(self, model: "TablesModel") -> None:
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
