import logging
from typing import (
    TYPE_CHECKING,
    Callable,
    Generic,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from exdrf.constants import RecIdType
from PyQt5.QtCore import QModelIndex, QPoint, Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.crud_actions import (
    AcBase,
    OpenCreateAc,
    OpenDeleteAc,
    OpenEditAc,
    OpenViewAc,
)
from exdrf_qt.controls.filter_dlg.filter_dlg import FilterDlg
from exdrf_qt.controls.search_lines.with_model import ModelSearchLine
from exdrf_qt.controls.tree_header import ListDbHeader
from exdrf_qt.models.field import NO_EDITOR_VALUE
from exdrf_qt.utils.tlh import top_level_handler

if TYPE_CHECKING:
    from PyQt5.QtCore import QItemSelection, QItemSelectionModel  # noqa: F401

    from exdrf_qt.context import QtContext  # noqa: F401
    from exdrf_qt.controls.search_lines.base import SearchData
    from exdrf_qt.models import QtModel  # noqa: F401
    from exdrf_qt.models.field import QtField  # noqa: F401
    from exdrf_qt.models.record import QtRecord  # noqa: F401

DBM = TypeVar("DBM")
logger = logging.getLogger(__name__)


class ListDb(QWidget, QtUseContext, Generic[DBM]):
    """A list that presents the content of a database table.

    Attributes:
        ly: The layout of the list.
        h_ly: The horizontal layout of the list.
        tree: The tree view that presents the content of the list.
        c_search_box: The search box that allows the user to search for items.
        lbl_total: The label that displays the total number of items.
        lbl_loaded: The label that displays the number of loaded items.
        lbl_in_prog: The label that displays the number of items in progress.
    """

    ly: QVBoxLayout
    h_ly: QHBoxLayout
    tree: "TreeViewDb[DBM]"
    c_search_box: "ModelSearchLine"
    lbl_total: QLabel
    lbl_loaded: QLabel
    lbl_in_prog: QLabel

    def __init__(
        self,
        ctx: "QtContext",
        parent: Optional["QWidget"] = None,
        menu_handler: Optional[Callable] = None,
        other_actions: Optional[
            List[Union[Tuple[str, str, str], "AcBase", QAction, None]]
        ] = None,
    ):
        super().__init__(parent=parent)
        self.ctx = ctx

        self.ly = QVBoxLayout()
        self.ly.setContentsMargins(1, 1, 1, 1)
        self.ly.setSpacing(1)

        self.tree = TreeViewDb[DBM](
            ctx=ctx,
            parent=self,
            menu_handler=menu_handler,
            other_actions=other_actions,
        )
        self.ly.addWidget(self.tree)

        self.h_ly = QHBoxLayout()

        # Initialize the search line.
        self.c_search_box = ModelSearchLine(
            parent=self,
            ctx=self.ctx,
            model=None,  # type: ignore
        )
        self.c_search_box.setMaximumWidth(200)
        self.h_ly.addWidget(self.c_search_box)

        # Set focus to the search box when the widget is created
        # so that the user can start typing immediately.
        self.c_search_box.setFocus()

        self.lbl_total = QLabel(
            self.t("cmn.total_count", "Total: {count}", count=0), self
        )
        self.lbl_total.setContentsMargins(10, 0, 0, 0)
        self.h_ly.addWidget(self.lbl_total)

        self.lbl_loaded = QLabel(
            self.t("cmn.loaded_count", "Loaded: {count}", count=0), self
        )
        self.lbl_loaded.setContentsMargins(10, 0, 0, 0)
        self.h_ly.addWidget(self.lbl_loaded)

        self.lbl_in_prog = QLabel(
            self.t("cmn.in_progress_count", "In progress: {count}", count=0),
            self,
        )
        self.lbl_in_prog.setContentsMargins(10, 0, 0, 0)
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
        self.c_search_box.qt_model = model

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

    @top_level_handler
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

    @top_level_handler
    def on_request_completed(
        self,
        start: int,
        count: int,
        uniq_id: int,
        total_count: int,
    ) -> None:
        """Handle the request completed event."""
        self.on_request_issued(start, count, uniq_id, total_count)

    @top_level_handler
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

    def apply_simple_search(self, data: "SearchData") -> None:
        """Apply a simple search to the model."""
        self.qt_model.apply_simple_search(data.term, data.search_type)


class DbFieldDelegate(QStyledItemDelegate):
    """Delegate that edits model fields using QtField editors."""

    def _field_from_index(self, index: QModelIndex) -> Optional["QtField"]:
        """Resolve the QtField for a model index.

        Args:
            index: The model index being edited.

        Returns:
            The QtField instance or None if not available.
        """
        model = index.model()
        if model is None or not hasattr(model, "column_fields"):
            return None
        fields = getattr(model, "column_fields", None)
        if not fields or index.column() >= len(fields):
            return None
        return fields[index.column()]

    def createEditor(
        self,
        parent: Optional[QWidget],
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> Optional[QWidget]:
        """Create an editor widget for the given index."""
        field = self._field_from_index(index)
        if field is None or not field.is_editable():
            return None

        editor = field.create_editor(parent)
        if editor is None:
            return None

        def _commit_and_close(target: QWidget) -> None:
            self.commitData.emit(target)
            try:
                self.closeEditor.emit(target)  # type: ignore[arg-type]
            except Exception:
                logger.exception("Failed to close inline editor")

        field.configure_editor(editor, _commit_and_close)
        return editor

    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        """Populate the editor with the current value."""
        field = self._field_from_index(index)
        if field is None:
            return
        value = index.data(Qt.ItemDataRole.EditRole)
        field.set_editor_data(editor, value)

    def setModelData(self, editor: QWidget, model, index: QModelIndex) -> None:
        """Commit the editor value back to the model."""
        if model is None:
            return
        field = self._field_from_index(index)
        if field is None:
            return
        value = field.editor_value(editor)
        if value is NO_EDITOR_VALUE:
            return
        model.setData(index, value, Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(
        self, editor: QWidget, option: QStyleOptionViewItem, index: QModelIndex
    ) -> None:
        """Position the editor within the cell."""
        editor.setGeometry(option.rect)


class TreeViewDb(QTreeView, QtUseContext, Generic[DBM]):
    """A list that presents the content of a database table.

    The list includes some default actions. If you want to discard any of it
    call its .deleteLater() method and set it in this class to None.

    To edit, view, create and delete items the class uses the router, which
    needs a resource path. We assume that the names of the database model
    classes passed to the model (through setModel) are the same as the names
    of the resources in the router.

    Attributes:
        ac_new: Action to create a new item.
        ac_rem: Action to remove the selected item.
        ac_rem_all: Action to remove all items.
        ac_edit: Action to edit the selected item.
        ac_view: Action to view the selected item.
        ac_clone: Action to clone the selected item.
        ac_export: Action to export all items.
        ac_set_null: Action to set the selected item to NULL.
        ac_reload: Action to reload the items.
        ac_filter: Action to filter the items.
    """

    ac_new: OpenCreateAc
    ac_rem: OpenDeleteAc
    ac_rem_all: QAction
    ac_restore: QAction
    ac_edit: OpenEditAc
    ac_view: OpenViewAc
    ac_clone: QAction
    ac_export: QAction
    ac_set_null: QAction
    ac_reload: QAction
    ac_filter: QAction
    ac_others: List[Union["AcBase", QAction, None]]

    def __init__(
        self,
        ctx: "QtContext",
        parent: Optional["QWidget"] = None,
        menu_handler: Optional[Callable] = None,
        other_actions: Optional[
            List[Union[Tuple[str, str, str], "AcBase", QAction, None]]
        ] = None,
    ):
        super().__init__(parent=parent)
        self.ctx = ctx
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
        self.create_actions(other_actions)

        # Use custom header
        header = ListDbHeader(parent=self, ctx=ctx, qt_model=self.qt_model)
        self.setHeader(header)

        # Use a field-aware delegate for inline edits.
        self.setItemDelegate(DbFieldDelegate(self))

    @property
    def qt_model(self) -> "QtModel[DBM]":
        """The model that is used to present the data in the list."""
        return cast("QtModel[DBM]", self.model())

    @property
    def base_route(self) -> str:
        """The base route for the list."""
        try:
            m_name = self.qt_model.db_model.__name__
        except Exception:
            m_name = "unknown"
        return f"exdrf://navigation/resource/{m_name}"

    def setModel(self, model: "QtModel[DBM]") -> None:  # type: ignore[override]
        """Set the model for the list."""
        crt_model: Union[QItemSelectionModel, None] = self.selectionModel()
        if crt_model is not None:
            crt_model.selectionChanged.disconnect(self.on_selection_changed)

        super().setModel(model)

        # Update the CRUD actions to use the new model.
        base_route = self.base_route
        if self.ac_new is not None:
            self.ac_new.route = f"{base_route}/create"
        if self.ac_rem is not None:
            self.ac_rem.route = base_route
        if self.ac_edit is not None:
            self.ac_edit.route = base_route
        if self.ac_view is not None:
            self.ac_view.route = base_route

        # Connect the selection model to the on_selection_changed method.
        new_sel_model = self.selectionModel()
        if new_sel_model:
            new_sel_model.selectionChanged.connect(self.on_selection_changed)

        empty_model = model.total_count == 0

        if self.ac_rem_all is not None:
            self.ac_rem_all.setEnabled(not empty_model)
        if self.ac_export is not None:
            self.ac_export.setEnabled(not empty_model)
        if self.ac_filter is not None:
            self.ac_filter.setEnabled(not empty_model)
        if self.ac_new is not None:
            self.ac_new.setEnabled(True)

        header = self.header()
        if isinstance(header, ListDbHeader):
            header.qt_model = self.qt_model
            header.load_sections_from_settings()

    def create_actions(
        self,
        other_actions: Optional[
            List[Union[Tuple[str, str, str], "AcBase", QAction, None]]
        ] = None,
    ):
        """Create the actions.

        Note that we do not take a model as parameter in the constructor,
        so the model is not available at this time, so we create the
        CRUD actions with empty routes. The setModel() overloaded method
        updates the routes to the correct ones.
        """

        self.ac_new = OpenCreateAc(
            label=self.t("sq.common.new", "New"),
            ctx=self.ctx,
            route="",
            menu_or_parent=self,
        )

        self.ac_rem = OpenDeleteAc(
            label=self.t("sq.common.del", "Remove"),
            ctx=self.ctx,
            route="",
            menu_or_parent=self,
            id=self.get_selected_db_id,
        )

        self.ac_rem_all = QAction(
            self.get_icon("emotion_blow_current"),
            self.t("sq.common.del-all", "Remove all"),
            self,
        )
        self.ac_rem_all.triggered.connect(self.on_remove_all)

        self.ac_restore = QAction(
            self.get_icon("bin_recycle"),
            self.t("sq.common.restore", "Restore"),
            self,
        )
        self.ac_restore.triggered.connect(self.on_restore)

        self.ac_edit = OpenEditAc(
            label=self.t("sq.common.edit", "Edit"),
            ctx=self.ctx,
            route="",
            menu_or_parent=self,
            id=self.get_selected_db_id,
        )

        self.ac_view = OpenViewAc(
            label=self.t("sq.common.view", "View"),
            ctx=self.ctx,
            route="",
            menu_or_parent=self,
            id=self.get_selected_db_id,
        )

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

        # Create custom actions.
        self.ac_others = []
        if other_actions is not None:
            other_ac: Union["AcBase", QAction, None]
            for ac_src in other_actions:
                if isinstance(ac_src, tuple):
                    label, icon, route = ac_src
                    other_ac = AcBase(
                        label=label,
                        ctx=self.ctx,
                        route=route,
                        icon=self.get_icon(icon),
                        menu_or_parent=self,
                    )
                elif isinstance(ac_src, AcBase):
                    other_ac = ac_src
                elif ac_src is None:
                    other_ac = None
                elif callable(ac_src):
                    other_ac = ac_src(
                        ctx=self.ctx,
                        menu_or_parent=self,
                        provider=self,
                    )
                else:
                    raise ValueError(f"Invalid action: {ac_src}")
                self.ac_others.append(other_ac)

        self.addActions(
            [
                self.ac_new,
                self.ac_rem,
                self.ac_rem_all,
                self.ac_edit,
                self.ac_view,
                self.ac_clone,
                self.ac_export,
                self.ac_set_null,
                self.ac_reload,
                self.ac_filter,
                *[ac for ac in self.ac_others if ac is not None],
            ]
        )
        self.ac_new.setEnabled(True)
        self.ac_rem.setEnabled(False)
        self.ac_edit.setEnabled(False)
        self.ac_view.setEnabled(False)
        self.ac_set_null.setEnabled(False)
        self.ac_clone.setEnabled(False)

    def get_selected_db_id(self) -> Optional[RecIdType]:
        """Get the single selected item ID.

        This assumes that the model is a single-select model, but it does
        not check that there is a single selected item, it just
        returns the first one.

        If the item is in error or loading states the result is None.
        """
        model = self.qt_model
        selected_indexes = self.selectedIndexes()
        if not selected_indexes:
            return None

        # Get the first selected index.
        selected_index = selected_indexes[0]
        selected_row = selected_index.row()

        # Get the item at that index.
        record = model.data_record(selected_row)
        if record is None:
            return None
        if not record.loaded or record.error:
            return None
        return record.db_id

    def get_selected_records(
        self,
        exclude_error: bool = True,
        exclude_not_loaded: bool = True,
        exclude_top: bool = True,
    ) -> List["QtRecord"]:
        """Get the records of all selected items.

        Args:
            exclude_error: If True, exclude items that are in error state.
            exclude_not_loaded: If True, exclude items that are not loaded.
            exclude_top: If True, exclude items that are in the top cache,
                that is, items that are not directly managed by the model.
        """
        result = []
        model = self.qt_model
        # Collect the selected source records.
        src_sm = self.selectionModel()
        if src_sm is None:
            return result
        selected_rows = [i.row() for i in src_sm.selectedRows()]
        if not selected_rows:
            return result

        for row in selected_rows:
            record = model.data_record(row)
            if record is None:
                continue
            if exclude_error and record.error:
                continue
            if exclude_not_loaded and not record.loaded:
                continue
            if exclude_top and row < len(model.top_cache):
                continue
            result.append(record)
        return result

    def get_selected_db_ids(
        self,
        exclude_top: bool = True,
    ) -> List[RecIdType]:
        """Get the IDs of all selected items.

        The result set only includes items that are loaded and not in error.
        Other items are silently ignored.

        Args:
            exclude_top: If True, exclude items that are in the top cache,
                that is, items that are not directly managed by the model.
        """
        return [
            record.db_id
            for record in self.get_selected_records(exclude_top=exclude_top)
        ]

    def add_other_view_actions(self, menu: QMenu):
        """Add the other actions to the context menu."""
        actual_actions = 0
        for ac in self.ac_others:
            if ac is not None:
                menu.addAction(ac)
                actual_actions += 1
            else:
                menu.addSeparator()
        if actual_actions:
            menu.addSeparator()

    @top_level_handler
    def show_context_menu(self, point: "QPoint") -> None:
        """Show the context menu."""
        menu = QMenu(self)

        if self.ac_reload is not None:
            menu.addAction(self.ac_reload)

        if self.ac_filter is not None:
            menu.addAction(self.ac_filter)

        if self.ac_new is not None:
            menu.addSeparator()
            menu.addAction(self.ac_new)

        if self.ac_rem is not None:
            menu.addSeparator()
            menu.addAction(self.ac_rem)

        if self.ac_rem_all is not None:
            if self.ac_rem is None:
                menu.addSeparator()
            menu.addAction(self.ac_rem_all)

        self.add_other_view_actions(menu)

        if self.ac_view is not None:
            menu.addAction(self.ac_view)

        if self.ac_edit is not None:
            menu.addAction(self.ac_edit)

        if self.ac_set_null is not None:
            index = self.can_null_current_index()
            if index is not None:
                menu.addAction(self.ac_set_null)

        if self.ac_clone is not None:
            menu.addAction(self.ac_clone)

        if self.ac_export is not None:
            menu.addSeparator()
            menu.addAction(self.ac_export)

        # Show the menu.
        vp = self.viewport()
        assert vp is not None, "Viewport should not be None"
        menu.exec_(vp.mapToGlobal(point))

    @top_level_handler
    def on_selection_changed(
        self,
        selected: "QItemSelection",
        deselected: "QItemSelection",
    ) -> None:
        """Handle selection changes."""
        empty_sel = selected.isEmpty()

        if self.ac_rem is not None:
            self.ac_rem.setEnabled(not empty_sel)
        if self.ac_view is not None:
            self.ac_view.setEnabled(not empty_sel)
        if self.ac_edit is not None:
            self.ac_edit.setEnabled(not empty_sel)
        if self.ac_set_null is not None:
            self.ac_set_null.setEnabled(not empty_sel)
        if self.ac_clone is not None:
            self.ac_clone.setEnabled(not empty_sel)

        empty_model = self.qt_model.total_count == 0

        if self.ac_rem_all is not None:
            self.ac_rem_all.setEnabled(not empty_model)
        if self.ac_export is not None:
            self.ac_export.setEnabled(not empty_model)
        if self.ac_filter is not None:
            self.ac_filter.setEnabled(not empty_model)

        if self.ac_new is not None:
            self.ac_new.setEnabled(True)

    def _remove_all_records(self) -> None:
        """Default implementation for removing all records.

        It simply asks the model to remove all records.

        At this point the user confirmed the removal.
        """
        self.qt_model.remove_all_records()

    @top_level_handler
    def on_remove_all(self) -> None:
        """Remove all items."""
        if (
            QMessageBox.question(
                self,
                self.t("cmn.question", "Question"),
                self.t(
                    "cmn.question.remove-n-items",
                    "Are you sure you want to remove {count} items?",
                    count=self.qt_model.total_count,
                ),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            != QMessageBox.Yes
        ):
            return

        if not self.qt_model.has_soft_delete_field:
            if (
                QMessageBox.question(
                    self,
                    self.t("cmn.warning", "Warning"),
                    self.t(
                        "cmn.question.permanent-delete",
                        "WARNING!\n"
                        "\n"
                        "This database table does not support soft-delete.\n"
                        "All {count} items will be permanently deleted, \n"
                        "with no way of recovering them.\n"
                        "\n"
                        "Are REALLY REALLY sure you want to continue?",
                        count=self.qt_model.total_count,
                    ),
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                != QMessageBox.Yes
            ):
                return
        self._remove_all_records()

    def _clone_db_item(self, db_id: RecIdType) -> None:
        """Default implementation for cloning a database record.

        It simply asks the model to clone the record and scrolls to the new
        record.

        At this point the user has selected a single record to clone.

        Args:
            db_id: The ID of the record to clone.
        """
        index, _ = self.qt_model.clone_record(db_id)
        self.scrollTo(self.qt_model.index(index, 0))

    @top_level_handler
    def on_clone_selected(self) -> None:
        """Clone the selected item."""
        if not self.qt_model.can_clone_records():
            self.ctx.show_error(
                title=self.t("cmn.error", "Error"),
                message=self.t(
                    "cmn.error.cannot-clone",
                    "Cannot clone records.",
                ),
            )
            return

        db_ids = self.get_selected_db_ids()
        if not db_ids:
            self.ctx.show_error(
                title=self.t("cmn.error", "Error"),
                message=self.t(
                    "cmn.error.no-selected-records",
                    "No selected records to clone.",
                ),
            )
            return

        if len(db_ids) > 1:
            self.ctx.show_error(
                title=self.t("cmn.error", "Error"),
                message=self.t(
                    "cmn.error.cannot-clone-multiple",
                    "Cannot clone multiple records at once.",
                ),
            )
            return

        self._clone_db_item(db_ids[0])

    @top_level_handler
    def on_export_all(self) -> None:
        """Export all items."""
        raise NotImplementedError("on_export_all() not implemented.")

    def can_null_current_index(self):
        src_sm = self.selectionModel()
        if src_sm is None:
            return None
        column_fields = self.qt_model.column_fields
        index = src_sm.currentIndex()
        column = index.column()
        field: "QtField" = column_fields[column]
        return index if field.nullable and not field.read_only else None

    @top_level_handler
    def on_set_null(self) -> None:
        """Set the selected item to NULL."""
        index = self.can_null_current_index()
        if index is None:
            return

        if not self.qt_model.setData(index, None, Qt.ItemDataRole.EditRole):
            self.ctx.show_error(
                title=self.t("cmn.error", "Error"),
                message=self.t(
                    "cmn.error.cannot-set-null",
                    "Cannot set field to NULL.",
                ),
            )

    @top_level_handler
    def on_reload(self) -> None:
        """Reload the items."""
        model = cast("QtModel", self.model())
        model.reset_model()

    @top_level_handler
    def on_filter(self) -> None:
        """Filter the items."""
        # This is the general filter dialog, distinct from header column
        # filter
        dlg = FilterDlg(
            ctx=self.ctx,
            qt_model=self.qt_model,
            parent=self,
        )
        if dlg.exec_() == dlg.Accepted:
            try:
                self.qt_model.apply_filter(dlg.filter)  # type: ignore
            except Exception as e:
                self.ctx.show_error(
                    title=self.t("cmn.error", "Error"),
                    message=self.t(
                        "cmn.error.bad_filter",
                        "Invalid filter: {error}",
                        error=str(e),
                    ),
                )
                logger.exception("Error in ListDb.on_filter: bad filter")

    @top_level_handler
    def on_restore(self) -> None:
        """Restore the selected items."""
        del_ids = [
            rec.db_id
            for rec in self.get_selected_records(exclude_top=False)
            if rec.soft_del and rec.db_id
        ]
        if not del_ids:
            return
        self.qt_model.restore_records(del_ids)
