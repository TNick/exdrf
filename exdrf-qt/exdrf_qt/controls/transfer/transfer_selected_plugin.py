"""Database viewer plugin that adds 'Transfer selected' to the table viewer
context menu.
"""

import logging
from typing import TYPE_CHECKING, Callable, List, Optional

from exdrf_al.connection import DbConn
from PyQt5.QtWidgets import QAction, QProgressDialog

from exdrf_qt.controls.table_viewer import (
    TableViewCtx,
    TableViewer,
    ViewerPlugin,
)
from exdrf_qt.controls.transfer.transfer_rows_worker import TransferRowsWorker

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class TransferSelectedPlugin(ViewerPlugin):
    """Viewer plugin that transfers selected rows to a destination connection.

    Private Attributes:
        _dst: Destination connection used by this plugin.
        _on_done: Optional callback to invoke when the transfer finishes.
        _chunk: Batch size for inserts.
        _active_worker: Currently running worker (if any).
        _dlg: The QProgressDialog used for progress UI (if any).
    """

    # Private attributes
    _dst: DbConn
    _on_done: Optional[Callable[[], None]]
    _chunk: int
    _active_worker: Optional[TransferRowsWorker]
    _dlg: Optional[QProgressDialog]

    def __init__(
        self,
        *,
        dst: DbConn,
        on_done: Optional[Callable[[], None]] = None,
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
        self._active_worker = None
        self._dlg = None

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

        worker = TransferRowsWorker(
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
