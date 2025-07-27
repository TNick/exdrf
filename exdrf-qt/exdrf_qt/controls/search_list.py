from typing import TYPE_CHECKING, Generic, Optional, Type, TypeVar, cast

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QAction,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QLineEdit,
    QTreeView,
    QVBoxLayout,
)

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.search_line import SearchLine
from exdrf_qt.field_ed.base import DrfFieldEd

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext
    from exdrf_qt.controls.base_editor import ExdrfEditor
    from exdrf_qt.models import QtModel

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
    editor_class: Optional[Type["ExdrfEditor"]]
    ac_create: Optional[QAction]
    field: Optional["DrfFieldEd"] = None

    def __init__(
        self,
        ctx: "QtContext",
        qt_model: "QtModel[DBM]",
        parent=None,
        popup: bool = False,
        editor_class: Optional[Type["ExdrfEditor"]] = None,
        field: Optional["DrfFieldEd"] = None,
    ):
        super().__init__(parent)
        self.ctx = ctx
        self.editor_class = editor_class
        self.ac_create = None
        self.field = field

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
        self.prepare_search_line(qt_model)
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

    def prepare_search_line(self, qt_model: "QtModel[DBM]"):
        self.src_line = SearchLine(
            parent=self,
            callback=qt_model.apply_simple_search,
            ctx=self.ctx,
        )

        if self.editor_class is not None:
            self.ac_create = QAction(
                self.ctx.get_icon("plus"),
                self.ctx.t("cmn.create.title", "Create"),
                self,
            )
            self.ac_create.triggered.connect(self._on_create)
            self.src_line.addAction(
                self.ac_create, QLineEdit.ActionPosition.TrailingPosition
            )

    def _on_create(self):
        """Create a new item."""
        if self.editor_class is None:
            raise ValueError("editor_class is not set")

        dlg = QDialog()
        ly = QVBoxLayout()
        dlg.setLayout(ly)

        # Create the editor.
        editor = self.editor_class(
            ctx=self.ctx,
            db_model=self.qt_model.db_model,
            parent=dlg,
        )

        # Disconnect the save button from the base implementation and connect
        # it to our own.
        assert editor.btn_box is not None
        save_btn = editor.btn_box.button(QDialogButtonBox.StandardButton.Save)
        assert save_btn is not None
        save_btn.clicked.disconnect(editor.on_save)
        save_btn.clicked.connect(dlg.accept)

        cancel_btn = editor.btn_box.button(
            QDialogButtonBox.StandardButton.Cancel
        )
        assert cancel_btn is not None
        cancel_btn.clicked.disconnect()
        cancel_btn.clicked.connect(dlg.reject)

        ly.addWidget(editor)
        if self.field is not None:
            self.field.starting_new_dependent(editor)

        dlg.setWindowTitle(self.t("cmn.create.title", "Create"))
        dlg.setModal(True)
        dlg.setMinimumSize(400, 300)

        if dlg.exec_() == QDialog.Accepted:
            with self.ctx.same_session() as session:
                editor.db_record(save=True)
                session.expunge_all()
            # checked = self.qt_model.checked_ids or []
            # assert editor.record_id is not None
            # self.qt_model.checked_ids = set(
            #     [
            #         *checked,
            #         editor.record_id,
            #     ]
            # )
        dlg.close()
        dlg.deleteLater()
        editor.deleteLater()
