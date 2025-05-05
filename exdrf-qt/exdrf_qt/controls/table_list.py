import logging
from typing import (
    TYPE_CHECKING,
    Callable,
    Generic,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

from exdrf.constants import RecIdType
from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
    QHBoxLayout,
    QLabel,
    QMenu,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from PyQt5.QtCore import QItemSelection, QItemSelectionModel  # noqa: F401

    from exdrf_qt.context import QtContext  # noqa: F401
    from exdrf_qt.controls.base_editor import EditorDb  # noqa: F401
    from exdrf_qt.models import QtModel  # noqa: F401


DBM = TypeVar("DBM")
logger = logging.getLogger(__name__)


class ListDb(QWidget, QtUseContext, Generic[DBM]):
    """A list that presents the content of a database table."""

    def __init__(
        self,
        ctx: "QtContext",
        parent: Optional["QWidget"] = None,
        menu_handler: Optional[Callable] = None,
        editor: Optional[Type["EditorDb[DBM]"]] = None,
    ):
        super().__init__(parent=parent)
        self.ctx = ctx

        self.ly = QVBoxLayout(self)
        self.ly.setContentsMargins(0, 0, 0, 0)
        self.ly.setSpacing(0)

        self.tree = TreeViewDb[DBM](
            ctx=ctx,
            parent=self,
            menu_handler=menu_handler,
            editor=editor,
        )
        self.ly.addWidget(self.tree)

        self.h_ly = QHBoxLayout(self)

        self.lbl_total = QLabel(
            self.t("cmn.total_count", "Total: {count}", count=0), self
        )
        self.h_ly.addWidget(self.lbl_total)

        self.lbl_loaded = QLabel(
            self.t("cmn.loaded_count", "Loaded: {count}", count=0), self
        )
        self.h_ly.addWidget(self.lbl_loaded)

        self.lbl_in_prog = QLabel(
            self.t("cmn.in_progress_count", "In progress: {count}", count=0),
            self,
        )
        self.h_ly.addWidget(self.lbl_in_prog)

        self.ly.addLayout(self.h_ly)
        self.setLayout(self.ly)

    @property
    def qt_model(self) -> "QtModel[DBM]":
        """The model that is used to present the data in the list."""
        return self.tree.qt_model

    def setModel(self, model: "QtModel[DBM]") -> None:
        """Set the model for the list."""
        crt_m = self.qt_model
        if crt_m is not None:
            crt_m.totalCountChanged.disconnect(self.on_total_count_changed)
            crt_m.loadedCountChanged.disconnect(self.on_loaded_count_changed)
            crt_m.requestIssued.disconnect(self.on_request_issued)
            crt_m.requestCompleted.disconnect(self.on_request_completed)
            crt_m.requestError.disconnect(self.on_request_error)

        self.tree.setModel(model)

        if model is not None:
            model.totalCountChanged.connect(self.on_total_count_changed)
            model.loadedCountChanged.connect(self.on_loaded_count_changed)
            model.requestIssued.connect(self.on_request_issued)
            model.requestCompleted.connect(self.on_request_completed)
            model.requestError.connect(self.on_request_error)
            self.on_total_count_changed(model.total_count)
            self.on_loaded_count_changed(model.loaded_count)
            self.on_request_issued(0, 0, 0, len(model.requests))

    def on_total_count_changed(self, count: int) -> None:
        """Handle the total count changed event."""
        self.lbl_total.setText(
            self.t("sq.common.total", "Total: {count}", count=count)
        )

    def on_loaded_count_changed(self, count: int) -> None:
        """Handle the loaded count changed event."""
        self.lbl_loaded.setText(
            self.t("sq.common.loaded", "Loaded: {count}", count=count)
        )

    def on_request_issued(
        self,
        start: int,
        count: int,
        uniq_id: int,
        total_count: int,
    ) -> None:
        """Handle the request issued event."""
        self.lbl_in_prog.setText(
            self.t(
                "cmn.in_progress_count",
                "In progress: {count}",
                count=total_count,
            ),
        )

    def on_request_completed(
        self,
        start: int,
        count: int,
        uniq_id: int,
        total_count: int,
    ) -> None:
        """Handle the request completed event."""
        self.on_request_issued(start, count, uniq_id, total_count)

    def on_request_error(
        self,
        start: int,
        count: int,
        uniq_id: int,
        total_count: int,
        error: str,
    ) -> None:
        """Handle the request error event."""
        self.on_request_issued(start, count, uniq_id, total_count)


class TreeViewDb(QTreeView, QtUseContext, Generic[DBM]):
    """A list that presents the content of a database table.

    Attributes:
        editor: The editor that is used to create new items or edit the
            existing items.
        ac_new: Action to create a new item.
        ac_rem: Action to remove the selected item.
        ac_rem_all: Action to remove all items.
        ac_edit: Action to edit the selected item.
        ac_clone: Action to clone the selected item.
        ac_export: Action to export all items.
        ac_set_null: Action to set the selected item to NULL.
        ac_reload: Action to reload the items.
        ac_filter: Action to filter the items.
    """

    editor: Optional[Type["EditorDb[DBM]"]] = None

    ac_new: QAction
    ac_rem: QAction
    ac_rem_all: QAction
    ac_edit: QAction
    ac_clone: QAction
    ac_export: QAction
    ac_set_null: QAction
    ac_reload: QAction
    ac_filter: QAction

    def __init__(
        self,
        ctx: "QtContext",
        parent: Optional["QWidget"] = None,
        menu_handler: Optional[Callable] = None,
        editor: Optional[Type["EditorDb[DBM]"]] = None,
    ):
        super().__init__(parent=parent)
        self.ctx = ctx
        self.editor = editor
        self.setAlternatingRowColors(True)
        self.setRootIsDecorated(False)
        self.setSortingEnabled(True)
        self.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed
        )
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(
            menu_handler if menu_handler else self.show_context_menu
        )
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDragDropOverwriteMode(False)
        self.setUniformRowHeights(True)

        # Prepare the actions.
        self.create_actions()

    @property
    def qt_model(self) -> "QtModel[DBM]":
        """The model that is used to present the data in the list."""
        return cast("QtModel[DBM]", self.model())

    def setModel(self, model: "QtModel[DBM]") -> None:  # type: ignore[override]
        """Set the model for the list."""
        crt_model: Union[QItemSelectionModel, None] = self.selectionModel()
        if crt_model is not None:
            crt_model.selectionChanged.disconnect(self.on_selection_changed)
        super().setModel(model)
        new_model = self.selectionModel()
        if new_model:
            new_model.selectionChanged.connect(self.on_selection_changed)

        empty_model = model.total_count == 0

        self.ac_rem_all.setEnabled(not empty_model)
        self.ac_export.setEnabled(not empty_model)
        self.ac_filter.setEnabled(not empty_model)

    def create_actions(self):
        """Create the actions."""
        self.ac_new = QAction(
            self.get_icon("document_empty"),
            self.t("sq.common.new", "New"),
            self,
        )
        self.ac_new.triggered.connect(self.on_create_new)

        self.ac_rem = QAction(
            self.get_icon("cross"), self.t("sq.common.del", "Remove"), self
        )
        self.ac_rem.triggered.connect(self.on_remove_selected)

        self.ac_rem_all = QAction(
            self.get_icon("emotion_blow_current"),
            self.t("sq.common.del-all", "Remove all"),
            self,
        )
        self.ac_rem_all.triggered.connect(self.on_remove_all)

        self.ac_edit = QAction(
            self.get_icon("edit_button"), self.t("sq.common.edit", "Edit"), self
        )
        self.ac_edit.triggered.connect(self.on_edit_selected)

        self.ac_clone = QAction(
            self.get_icon("page_copy"), self.t("sq.common.clone", "Clone"), self
        )
        self.ac_clone.triggered.connect(self.on_clone_selected)

        self.ac_export = QAction(
            self.get_icon("layer_aspect_arrow"),
            self.t("sq.common.export", "Export"),
            self,
        )
        self.ac_export.triggered.connect(self.on_export_all)

        self.ac_set_null = QAction(
            self.get_icon("clear_to_null"),
            self.t("sq.common.clear", "Set to NULL"),
            self,
        )
        self.ac_set_null.triggered.connect(self.on_set_null)

        self.ac_reload = QAction(
            self.get_icon("arrow_refresh"),
            self.t("sq.common.reload", "Reload"),
            self,
        )
        self.ac_reload.triggered.connect(self.on_reload)

        self.ac_filter = QAction(
            self.get_icon("filter"), self.t("sq.common.filter", "Filter"), self
        )
        self.ac_filter.triggered.connect(self.on_filter)

        self.addActions(
            [
                self.ac_new,
                self.ac_rem,
                self.ac_rem_all,
                self.ac_edit,
                self.ac_clone,
                self.ac_export,
                self.ac_set_null,
                self.ac_reload,
                self.ac_filter,
            ]
        )
        self.ac_new.setEnabled(self.editor is not None)
        self.ac_rem.setEnabled(False)
        self.ac_edit.setEnabled(False)
        self.ac_set_null.setEnabled(False)
        self.ac_clone.setEnabled(False)

    def get_selected_db_id(self) -> Optional[RecIdType]:
        """ "Get the selected item ID."""
        model = self.qt_model
        selected_indexes = self.selectedIndexes()
        if not selected_indexes:
            return None

        # Get the first selected index.
        selected_index = selected_indexes[0]
        selected_row = selected_index.row()

        # Get the item at that index.
        if selected_row > len(model.cache) - 1:
            return None
        item = model.cache[selected_row]
        if not item.loaded:
            return None

        return item.db_id

    def show_context_menu(self, point: "QPoint") -> None:
        """Show the context menu."""
        menu = QMenu(self)

        menu.addAction(self.ac_reload)
        menu.addAction(self.ac_filter)
        menu.addSeparator()
        menu.addAction(self.ac_new)
        menu.addSeparator()
        menu.addAction(self.ac_rem)
        menu.addAction(self.ac_rem_all)
        menu.addSeparator()
        menu.addAction(self.ac_edit)
        menu.addAction(self.ac_set_null)
        menu.addAction(self.ac_clone)
        menu.addSeparator()
        menu.addAction(self.ac_export)

        # Show the menu.
        vp = self.viewport()
        assert vp is not None, "Viewport should not be None"
        menu.exec_(vp.mapToGlobal(point))

    def on_selection_changed(
        self,
        selected: "QItemSelection",
        deselected: "QItemSelection",
    ) -> None:
        """Handle selection changes."""
        try:
            have_editor = self.editor is not None
            empty_sel = selected.isEmpty()

            self.ac_rem.setEnabled(not empty_sel)
            self.ac_edit.setEnabled(not empty_sel and have_editor)
            self.ac_set_null.setEnabled(not empty_sel)
            self.ac_clone.setEnabled(not empty_sel)

            empty_model = self.qt_model.total_count == 0

            self.ac_rem_all.setEnabled(not empty_model)
            self.ac_export.setEnabled(not empty_model)
            self.ac_filter.setEnabled(not empty_model)

            self.ac_new.setEnabled(have_editor)
        except Exception as e:
            logger.exception("Error in ListDb.on_selection_changed")
            self.ctx.show_error(
                title=self.t("sq.common.error", "Error"),
                message=str(e),
            )

    def on_create_new(self) -> None:
        """Create a new item."""
        try:
            assert self.editor is not None, "Editor should not be None"
            editor = self.editor(  # type: ignore
                ctx=self.ctx,
                parent=None,
            )
            self.ctx.create_window(editor)
            editor.set_record(None)
            editor.on_create_new()
        except Exception as e:
            logger.exception("Error in ListDb.on_create_new")
            self.ctx.show_error(
                title=self.t("sq.common.error", "Error"),
                message=str(e),
            )

    def on_remove_selected(self) -> None:
        """Remove the selected item."""
        try:
            raise NotImplementedError("on_remove_selected() not implemented.")
        except Exception as e:
            logger.exception("Error in ListDb.on_remove_selected")
            self.ctx.show_error(
                title=self.t("sq.common.error", "Error"),
                message=str(e),
            )

    def on_remove_all(self) -> None:
        """Remove all items."""
        try:
            raise NotImplementedError("on_remove_all() not implemented.")
        except Exception as e:
            logger.exception("Error in ListDb.on_remove_all")
            self.ctx.show_error(
                title=self.t("sq.common.error", "Error"),
                message=str(e),
            )

    def on_edit_selected(self) -> None:
        """Edit the selected item."""
        try:
            rec_id = self.get_selected_db_id()
            if rec_id is None:
                return

            assert self.editor is not None, "Editor should not be None"
            editor = self.editor(  # type: ignore
                ctx=self.ctx,
                parent=None,
                record_id=rec_id,
            )
            self.ctx.create_window(editor)
            # TODO remove editor.set_record(rec_id)
            editor.on_begin_edit()
        except Exception as e:
            logger.exception("Error in ListDb.on_edit_selected")
            self.ctx.show_error(
                title=self.t("sq.common.error", "Error"),
                message=str(e),
            )

    def on_clone_selected(self) -> None:
        """Clone the selected item."""
        try:
            raise NotImplementedError("on_clone_selected() not implemented.")
        except Exception as e:
            logger.exception("Error in ListDb.on_clone_selected")
            self.ctx.show_error(
                title=self.t("sq.common.error", "Error"),
                message=str(e),
            )

    def on_export_all(self) -> None:
        """Export all items."""
        try:
            raise NotImplementedError("on_export_all() not implemented.")
        except Exception as e:
            logger.exception("Error in ListDb.on_export_all")
            self.ctx.show_error(
                title=self.t("sq.common.error", "Error"),
                message=str(e),
            )

    def on_set_null(self) -> None:
        """Set the selected item to NULL."""
        try:
            raise NotImplementedError("on_set_null() not implemented.")
        except Exception as e:
            logger.exception("Error in ListDb.on_set_null")
            self.ctx.show_error(
                title=self.t("sq.common.error", "Error"),
                message=str(e),
            )

    def on_reload(self) -> None:
        """Reload the items."""
        try:
            model = cast("QtModel", self.model())
            model.reset_model()
        except Exception as e:
            logger.exception("Error in ListDb.on_reload")
            self.ctx.show_error(
                title=self.t("sq.common.error", "Error"),
                message=str(e),
            )

    def on_filter(self) -> None:
        """Filter the items."""
        try:
            raise NotImplementedError("on_filter() not implemented.")
        except Exception as e:
            logger.exception("Error in ListDb.on_filter")
            self.ctx.show_error(
                title=self.t("sq.common.error", "Error"),
                message=str(e),
            )
