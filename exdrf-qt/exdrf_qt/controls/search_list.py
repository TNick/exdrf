from typing import TYPE_CHECKING, Generic, TypeVar, cast

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QTreeView, QVBoxLayout

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext
    from exdrf_qt.models import QtModel

from PyQt5.QtCore import pyqtSignal

from exdrf_qt.controls.search_line import SearchLine

DBM = TypeVar("DBM")


class TreeView(QTreeView):
    """A tree view that emits a signal when the Enter key is pressed."""

    returnPressed = pyqtSignal(int)

    def keyPressEvent(self, event):
        assert event is not None
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            index = self.currentIndex()
            if index.isValid():
                self.returnPressed.emit(index.row())
        else:
            super().keyPressEvent(event)


class SearchList(QFrame, QtUseContext, Generic[DBM]):
    """A widget that allows th user to search for items in a list.

    It consists of a search line and a tree view to display the results. The
    search is applied to all the fields reported by the model through the
    `simple_search_fields` property. The search is applied to the database
    using the `ilike` operator.

    Attributes:
        ctx: The context that indicates the database connection.
        ly: The layout of the widget.
        src_line: The line edit for the search term.
        tree: The tree view to display the results.
        _search_timer: The timer to apply the search term after a delay.
    """

    ly: QVBoxLayout
    src_line: SearchLine
    tree: TreeView

    def __init__(
        self,
        ctx: "QtContext",
        qt_model: "QtModel[DBM]",
        parent=None,
        popup: bool = False,
    ):
        super().__init__(parent)
        self.ctx = ctx

        if popup:
            # Set up the frame
            self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
            self.setWindowFlags(
                cast(
                    Qt.WindowType,
                    Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint,
                )
            )

        self.ly = QVBoxLayout()

        # Initialize the search line.
        self.src_line = SearchLine(
            parent=self,
            callback=qt_model.apply_simple_search,
            ctx=self.ctx,
        )
        self.ly.addWidget(self.src_line)

        # Initialize the tree.
        self.tree = TreeView(self)
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(QTreeView.SingleSelection)
        self.tree.setSelectionBehavior(QTreeView.SelectRows)
        self.tree.setRootIsDecorated(False)
        self.tree.setModel(qt_model)
        self.tree.setHeaderHidden(True)
        self.ly.addWidget(self.tree)

        # Finalize the layout.
        self.ly.setContentsMargins(1, 1, 1, 1)
        self.ly.setSpacing(1)
        self.setLayout(self.ly)

    @property
    def qt_model(self) -> "QtModel[DBM]":
        """Get the model of the tree view."""
        return self.tree.model()  # type: ignore[return-value]
