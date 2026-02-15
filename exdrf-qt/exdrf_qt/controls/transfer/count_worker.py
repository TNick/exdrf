"""Worker thread that computes table row counts for the tables model."""

import logging
import time
from typing import TYPE_CHECKING, Optional

from PyQt5.QtCore import QThread, pyqtSignal

from .count_cache import count_cache, make_pair_key

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
    # New: emit both src and dst counts for a row when available
    counts_pair_ready = pyqtSignal(int, int, int)
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
        """Main worker loop. Uses up to two DB connections (src/dst)."""
        logger.log(
            VERBOSE,
            "CountWorker: started name=%s",
            self.objectName(),
        )
        # Open both connections if available
        conn_src = self._model._src_conn
        conn_dst = self._model._dst_conn
        if conn_src is None and conn_dst is None:
            logger.log(
                VERBOSE,
                "CountWorker: no connections for model side=%s, exiting",
                self._model._side,
            )
            return
        eng_src = conn_src.connect() if conn_src else None
        eng_dst = conn_dst.connect() if conn_dst else None
        db_src = eng_src.connect() if eng_src else None
        db_dst = eng_dst.connect() if eng_dst else None
        pair_key = make_pair_key(conn_src, conn_dst)

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

                # Check local cache in the model and shared cache
                r = self._model._rows[row]
                local_src = r.cnt_src
                local_dst = r.cnt_dst
                cached_src, cached_dst = count_cache.get_pair(pair_key, tbl)

                def _known(v: Optional[int]) -> bool:
                    return v is not None

                if local_src is not None:
                    cached_src = local_src  # prefer local
                if local_dst is not None:
                    cached_dst = local_dst

                # If both sides known, just emit and continue
                if cached_src is not None and cached_dst is not None:
                    self.counts_pair_ready.emit(row, cached_src, cached_dst)
                    continue

                # Try to reserve counting for this table; if not reserved, wait
                if not count_cache.reserve(pair_key, tbl):
                    waited = 0.0
                    # Wait up to ~2 seconds for the other worker to fill cache
                    while not self._stop and waited < 2.0:
                        time.sleep(0.02)
                        waited += 0.02
                        c_src, c_dst = count_cache.get_pair(pair_key, tbl)
                        if c_src is not None and c_dst is not None:
                            self.counts_pair_ready.emit(row, c_src, c_dst)
                            break
                    else:
                        # Attempt to reserve again; if still not possible skip
                        if not count_cache.reserve(pair_key, tbl):
                            # Give up for now; requeue lightly by continuing
                            continue

                # Perform counts for missing sides and update cache
                try:
                    # Build definitive integer values for both sides
                    if cached_src is not None:
                        src_val: int = cached_src
                    else:
                        if db_src is not None:
                            (v, err_msg, is_fatal) = (
                                self._model._count_with_connection(
                                    db_src,
                                    conn_src.schema if conn_src else "",
                                    tbl,
                                )
                            )
                            if err_msg is not None:
                                src_val = -1
                                if is_fatal:
                                    self.count_error.emit(err_msg)
                                    self._stop = True
                                    break
                            else:
                                src_val = int(v) if v is not None else -1
                        else:
                            src_val = -1

                    if cached_dst is not None:
                        dst_val: int = cached_dst
                    else:
                        if db_dst is not None:
                            (v, err_msg, is_fatal) = (
                                self._model._count_with_connection(
                                    db_dst,
                                    conn_dst.schema if conn_dst else "",
                                    tbl,
                                )
                            )
                            if err_msg is not None:
                                dst_val = -1
                                if is_fatal:
                                    self.count_error.emit(err_msg)
                                    self._stop = True
                                    break
                            else:
                                dst_val = int(v) if v is not None else -1
                        else:
                            dst_val = -1

                    # Update shared cache and emit for this model
                    count_cache.set_pair(pair_key, tbl, src_val, dst_val)
                    self.counts_pair_ready.emit(row, src_val, dst_val)
                finally:
                    # Ensure we release reservation
                    count_cache.release(pair_key, tbl)
        finally:
            if db_src is not None:
                try:
                    db_src.close()
                except Exception as e:
                    logger.log(
                        1,
                        "CountWorker: error closing src: %s",
                        e,
                        exc_info=True,
                    )
            if db_dst is not None:
                try:
                    db_dst.close()
                except Exception as e:
                    logger.log(
                        1,
                        "CountWorker: error closing dst: %s",
                        e,
                        exc_info=True,
                    )
        logger.log(
            VERBOSE,
            "CountWorker: stopped name=%s",
            self.objectName(),
        )
