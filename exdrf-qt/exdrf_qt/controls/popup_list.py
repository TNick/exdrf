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
)
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.new_search_line import SearchLine
from exdrf_qt.controls.tree_list import TreeView
from exdrf_qt.models import QtModel

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401

logger = logging.getLogger(__name__)


DBM = TypeVar("DBM", bound="PopupWidget")


class PopupWidget(QWidget, Generic[DBM], QtUseContext):
    """A widget that shows a list of items in a popup and allows the user
    to filter them.

    Attributes:
        tree: The tree view that shows the list of items.
        filter_edit: The line edit that allows the user to filter the list.
        qt_model: The model that provides the data.
        progress: The progress bar that shows the progress of the search.
        progress_timer: The timer that shows the progress bar.
    """

    tree: "TreeView"
    filter_edit: "SearchLine"
    qt_model: "QtModel[DBM]"
    progress: QProgressBar
    progress_timer: Optional[QTimer]

    def __init__(
        self,
        ctx: "QtContext",
        qt_model: Union["QtModel[DBM]", Type["QtModel[DBM]"]],
        parent=None,
        add_kb: Optional[Callable[[str], None]] = None,
    ):
        logger.log(1, "PopupWidget.__init__()")

        super().__init__(parent, Qt.WindowType.Popup)

        self.ctx = ctx
        self.progress_timer = None
        self.progress = None  # type: ignore

        if qt_model is not None and not isinstance(qt_model, QtModel):
            qt_model = qt_model(ctx=ctx, db_model=None)  # type: ignore
            logger.log(1, "PopupWidget created the new model")
        self.qt_model = qt_model

        self.setWindowFlags(Qt.WindowType.Popup)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.filter_edit = SearchLine(
            parent=self,
            ctx=ctx,
            add_button=add_kb is not None,
        )
        self.filter_edit.searchTermChanged.connect(qt_model.apply_simple_search)
        if add_kb is not None:
            self.filter_edit.addButtonClicked.connect(add_kb)

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
