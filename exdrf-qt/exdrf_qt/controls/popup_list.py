import logging
from contextlib import contextmanager
from typing import (
    TYPE_CHECKING,
    Callable,
    Generic,
    Optional,
    Type,
    TypeVar,
    Union,
)

from PyQt5.QtCore import (
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.search_lines.with_model import ModelSearchLine
from exdrf_qt.controls.tree_list import TreeView
from exdrf_qt.models import QtModel

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from exdrf_qt.controls.search_lines.base import SearchData

logger = logging.getLogger(__name__)
VERBOSE = 10


DBM = TypeVar("DBM")


class PopupWidget(QWidget, Generic[DBM], QtUseContext):
    """A widget that shows a list of items in a popup and allows the user
    to filter them.

    Attributes:
        tree: The tree view that shows the list of items.
        filter_edit: The line edit that allows the user to filter the list.
        qt_model: The model that provides the data.
        progress: The progress bar that shows the progress of the search.
        progress_timer: The timer that shows the progress bar.
    closed: Signal emitted when the popup hides.
    """

    closed = pyqtSignal(bool)

    tree: "TreeView"
    filter_edit: "ModelSearchLine"
    qt_model: "QtModel[DBM]"
    progress: QProgressBar
    progress_timer: Optional[QTimer]
    add_kb: Optional[Callable[[str], None]]
    _close_cancelled: bool

    def __init__(
        self,
        ctx: "QtContext",
        qt_model: Union["QtModel[DBM]", Type["QtModel[DBM]"]],
        parent=None,
        add_kb: Optional[Callable[[str], None]] = None,
    ):
        logger.log(VERBOSE, "PopupWidget.__init__()")

        super().__init__(parent, Qt.WindowType.Popup)

        self.ctx = ctx
        self.progress_timer = None
        self.progress = None  # type: ignore
        self.add_kb = add_kb
        self._close_cancelled = False

        if qt_model is not None and not isinstance(qt_model, QtModel):
            qt_model = qt_model(ctx=ctx, db_model=None)  # type: ignore
            logger.log(VERBOSE, "PopupWidget created the new model")
        self.qt_model = qt_model

        self.setWindowFlags(Qt.WindowType.Popup)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.filter_edit = ModelSearchLine(
            parent=self,
            ctx=ctx,
            add_button=(
                self.on_add_button_clicked if add_kb is not None else False
            ),
            model=qt_model,
        )

        self.create_tree()
        self.create_progress()

        layout = QVBoxLayout(self)
        layout.addWidget(self.tree)
        layout.addWidget(self.progress)
        layout.addWidget(self.filter_edit)
        layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(layout)

        self.qt_model.requestIssued.connect(self.request_items_start)
        self.qt_model.requestCompleted.connect(self.request_items_ok)
        self.qt_model.requestError.connect(self.request_items_error)

    def keyPressEvent(self, a0: Optional[QKeyEvent]) -> None:
        """Handle key presses that should close the popup.

        Args:
            event: The key event.
        """

        # Track the close reason before hiding the popup.
        if a0 is not None and a0.key() in (
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
        ):
            self._close_cancelled = False
            self.hide()
            return

        if a0 is not None and a0.key() == Qt.Key.Key_Escape:
            self._close_cancelled = True
            self.hide()
            return

        super().keyPressEvent(a0)

    def hideEvent(self, event) -> None:  # type: ignore[override]
        """Emit the closed signal when the popup hides.

        Args:
            event: The hide event.
        """

        # Notify listeners that the popup was closed.
        cancelled = self._close_cancelled
        self._close_cancelled = False
        self.closed.emit(cancelled)
        super().hideEvent(event)

    def on_search_data_changed(self, search_data: "SearchData"):
        if self.qt_model is None:
            raise ValueError("qt_model is not set")
        self.qt_model.apply_simple_search(
            search_data.term, search_data.search_type
        )

    def on_add_button_clicked(self):
        if self.add_kb is None:
            raise ValueError("add_kb is not set")
        self.add_kb(self.filter_edit.search_data.term or "")

    def create_tree(self):
        """Create the tree-view that shows search results."""

        self.tree = TreeView[DBM](self)
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.tree.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.tree.setRootIsDecorated(False)
        self.tree.setModel(self.qt_model)
        self.tree.setHeaderHidden(True)
        return self.tree

    def create_progress(self):
        """Create the progress bar that shows the progress of the search."""
        progress = QProgressBar(self)
        progress.setRange(0, 0)
        progress.setValue(0)
        progress.setTextVisible(False)
        progress.setFixedHeight(4)
        progress.setStyleSheet(
            """
            QProgressBar {
                border: none;
                background-color: #e0e0e0;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #3b99fc;
                border-radius: 2px;
            }
        """
        )
        progress.setVisible(False)
        self.progress = progress
        return progress

    def schedule_progress_show(self):
        """Schedule the progress bar to be shown."""
        if self.progress_timer is None:
            self.progress_timer = QTimer(self)
            self.progress_timer.setSingleShot(True)
            self.progress_timer.setInterval(500)
            self.progress_timer.timeout.connect(self.progress_show)
        self.progress_timer.start()

    def progress_show(self):
        """Show the progress bar."""
        if len(self.qt_model.requests) > 0:
            self.progress.setVisible(True)

    def change_progress(self, value: int):
        """Change the progress bar value."""
        if value <= 0:
            self.progress.setVisible(False)
            return
        if not self.progress.isVisible():
            self.schedule_progress_show()

    def request_items_start(
        self, req_id: int, start: int, count: int, in_progress: int
    ) -> None:
        """A request for items is issued.

        Args:
            req_id: The request ID.
            start: The starting index.
            count: The number of items that were loaded in this request.
            in_progress: The number of requests in progress, including this one.
        """
        self.change_progress(in_progress)

    def request_items_ok(
        self, req_id: int, start: int, count: int, in_progress: int
    ) -> None:
        """A request for items is completed.

        Args:
            req_id: The request ID.
            start: The starting index.
            count: The number of items to load.
            in_progress: The number of requests in progress, excluding this one.
        """
        self.change_progress(in_progress)

    def request_items_error(
        self, req_id: int, start: int, count: int, in_progress: int, error: str
    ) -> None:
        """A request for items generates an error.

        Args:
            req_id: The request ID.
            start: The starting index.
            count: The number of items to load.
            in_progress: The number of requests in progress, excluding this one.
            error: The error message.
        """
        self.change_progress(in_progress)

    @contextmanager
    def block_signals(self):
        """Block the signals of the widget."""
        self.filter_edit.blockSignals(True)
        self.tree.blockSignals(True)
        try:
            yield
        finally:
            self.filter_edit.blockSignals(False)
            self.tree.blockSignals(False)
