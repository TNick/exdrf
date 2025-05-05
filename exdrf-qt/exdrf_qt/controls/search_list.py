from typing import TYPE_CHECKING, Generic, Optional, TypeVar, cast

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QLineEdit, QTreeView, QVBoxLayout

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext
    from exdrf_qt.models import QtModel

from PyQt5.QtCore import QTimer, pyqtSignal

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
    src_line: QLineEdit
    tree: TreeView
    _search_timer: Optional[QTimer]

    def __init__(
        self,
        ctx: "QtContext",
        model: "QtModel[DBM]",
        parent=None,
        popup: bool = False,
    ):
        super().__init__(parent)
        self.ctx = ctx
        self._search_timer = None

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
        self.src_line = QLineEdit(self)
        label = self.t("cmn.search.term", "Enter search term")
        self.src_line.setPlaceholderText(label)
        self.src_line.setToolTip(label)
        self.src_line.setWhatsThis(label)
        self.src_line.setClearButtonEnabled(True)
        self.src_line.textChanged.connect(self.on_search_term_changed)
        self.ly.addWidget(self.src_line)

        # Initialize the tree.
        self.tree = TreeView(self)
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(QTreeView.SingleSelection)
        self.tree.setSelectionBehavior(QTreeView.SelectRows)
        self.tree.setRootIsDecorated(False)
        self.tree.setModel(model)
        self.tree.setHeaderHidden(True)
        self.ly.addWidget(self.tree)

        # Finalize the layout.
        self.ly.setContentsMargins(1, 1, 1, 1)
        self.ly.setSpacing(1)
        self.setLayout(self.ly)

    @property
    def model(self) -> "QtModel[DBM]":
        """Get the model of the tree view."""
        return self.tree.model()  # type: ignore[return-value]

    def on_search_term_changed(self, term: str) -> None:
        """Set the search term in the line edit.

        The function will wait for 500 ms after the user stops typing before
        applying the search term. This is to avoid applying the search term too
        frequently and to improve performance.
        """
        if term == "":
            # Be quick when the user clears the search term.
            self.model.filters = []
            self.model.reset_model()
            return

        if self._search_timer is None:
            self._search_timer = QTimer(self)
            self._search_timer.setSingleShot(True)
            self._search_timer.setInterval(500)
        else:
            self._search_timer.stop()
            self._search_timer.disconnect()
        self._search_timer.timeout.connect(lambda: self._apply_search(term))
        self._search_timer.start()

    def _apply_search(self, term: str) -> None:
        """Set the search term in the line edit."""
        model = self.model
        if len(term) == 0:
            self.model.filters = []
        else:
            if "%" not in term:
                term = f"%{term}%"
            term = term.replace(" ", "%")
            or_list = []
            for f in model.simple_search_fields:
                or_list.append(
                    {
                        "fld": f.name,
                        "op": "ilike",
                        "vl": term,
                    }
                )
            model.filters = ["or", or_list]  # type: ignore[assignment]
        model.reset_model()
