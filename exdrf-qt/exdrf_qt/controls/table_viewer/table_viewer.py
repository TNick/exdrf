"""Tabbed table viewer widget with per-column filters and plugins."""

import csv
import io
import json
import logging
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

import yaml
from PyQt5.QtCore import QPoint, Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
    QApplication,
    QDialog,
    QHeaderView,
    QMenu,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.filter_header import FilterHeader
from exdrf_qt.controls.table_viewer.column_filter_proxy import ColumnFilterProxy
from exdrf_qt.controls.table_viewer.column_visibility_dialog import (
    ColumnVisibilityDialog,
)
from exdrf_qt.controls.table_viewer.sql_column_delegate import (
    SqlColumnDelegate,
    TableCellDelegate,
)
from exdrf_qt.controls.table_viewer.sql_table_model import (
    SqlTableModel,
    get_foreign_key_columns,
)
from exdrf_qt.controls.table_viewer.table_view_ctx import TableViewCtx
from exdrf_qt.controls.table_viewer.viewer_plugin import ViewerPlugin
from exdrf_qt.utils.stay_open_menu import StayOpenMenu

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

    from exdrf_qt.context import QtContext

logger = logging.getLogger(__name__)
VERBOSE = 1


class TableViewer(QWidget, QtUseContext):
    """Generic tabbed table viewer with per-column filters and plugins.

    Attributes:
        ctx: The application context.

    Signals:
        all_tabs_closed: Emitted when the last tab is closed (tab count
            becomes 0). This is useful for UI elements that need to know when
            all tabs are closed, such as the database viewer.

    Private Attributes:
        _tabs: The QTabWidget hosting open tables.
        _plugins: Installed viewer plugins.
        _views: Context list for each open tab.
        _editing_allowed: Whether the Editing menu and per-tab edit mode
            are available.
        _column_editable_checks: List of callables (engine, schema, table,
            column_name) -> bool; if non-empty, a column is editable only
            if at least one returns True.
        _fk_columns_cache: Cache of get_foreign_key_columns result keyed by
            (engine_url, schema, table) for faster context menu display.
    """

    all_tabs_closed = pyqtSignal()

    # Public attributes
    ctx: "QtContext"

    # Private attributes
    _tabs: QTabWidget
    _plugins: List[ViewerPlugin]
    _views: List[TableViewCtx]
    _editing_allowed: bool
    _column_editable_checks: List[
        Callable[[object, Optional[str], str, str], bool]
    ]
    _fk_columns_cache: Dict[
        Tuple[str, str, str], List[Tuple[str, str, List[str]]]
    ]

    def __init__(
        self,
        ctx: "QtContext",
        parent: Optional[QWidget] = None,
        *,
        editing_allowed: bool = True,
    ) -> None:
        """Initialize the viewer widget.

        Args:
            ctx: Application context.
            parent: Optional parent widget.
            editing_allowed: If True, the context menu shows an Editing
                checkbox to toggle per-tab edit mode; if False, editing
                cannot be enabled and the menu item is hidden.
        """
        super().__init__(parent)
        self.ctx = ctx
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._tabs = QTabWidget(self)
        self._tabs.setTabsClosable(True)
        self._fk_columns_cache = {}
        self._tabs.tabCloseRequested.connect(self._close_tab)
        ly = QVBoxLayout(self)
        ly.setContentsMargins(2, 2, 2, 2)
        ly.addWidget(self._tabs)
        self._plugins = []
        self._views = []
        self._editing_allowed = editing_allowed
        self._column_editable_checks = []

    def add_plugin(self, plugin: ViewerPlugin) -> None:
        """Install a plugin that contributes actions and hooks.

        Args:
            plugin: The plugin instance to add.
        """
        self._plugins.append(plugin)
        logger.log(
            VERBOSE, "TableViewer: plugin added %s", type(plugin).__name__
        )

    def add_column_editable_check(
        self,
        fn: Callable[[object, Optional[str], str, str], bool],
    ) -> None:
        """Register a check to decide if a column is editable.

        When any check is registered, a column is editable only if at least
        one check returns True for (engine, schema, table_name, column_name).
        If no check is registered, all columns are considered editable when
        the tab is in editing mode.

        Args:
            fn: Callable(engine, schema, table_name, column_name) -> bool.
        """
        self._column_editable_checks.append(fn)

    def open_table(
        self,
        *,
        engine: "Engine",
        schema: Optional[str],
        table: str,
        tab_label: Optional[str] = None,
        user_extra_columns: Optional[List[Tuple[str, str, str]]] = None,
        workspace_state: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Open a table in a new tab.

        Args:
            engine: Engine to read from.
            schema: Optional schema name.
            table: Table name (used for loading data).
            tab_label: Optional label for the tab; if None, uses table.
            user_extra_columns: Optional user-added join columns (from workspace
                load); merged with plugin default columns.
            workspace_state: Optional state dict to apply after the tab is
                created (column order, filters, sort).
        """
        label = tab_label if tab_label is not None else table
        logger.log(
            VERBOSE, "TableViewer: open_table table=%s schema=%s", table, schema
        )
        default_extra: List[Tuple[str, str, str]] = []
        for plg in self._plugins:
            try:
                extra = plg.get_default_join_columns(
                    self, engine, schema, table
                )
                if extra:
                    default_extra.extend(extra)
            except Exception:
                logger.debug(
                    "get_default_join_columns failed for %s",
                    type(plg).__name__,
                    exc_info=True,
                )
        user_extra = user_extra_columns or []
        all_extra = list(default_extra) + list(user_extra)
        model = SqlTableModel(
            engine=engine,
            schema=schema,
            table=table,
            extra_columns=all_extra if all_extra else None,
        )
        proxy = ColumnFilterProxy()
        proxy.setSourceModel(model)

        # Create and configure view
        view = QTableView(self)
        view.setModel(proxy)
        hh = view.horizontalHeader()
        assert hh is not None
        hh.setSectionResizeMode(QHeaderView.Stretch)
        view.setSelectionBehavior(QAbstractItemView.SelectRows)
        view.setAlternatingRowColors(True)
        view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        view.customContextMenuRequested.connect(
            lambda p, v=view: self._show_context_menu(v, p)
        )

        # Setup per-column filter header and wire it to proxy
        header = FilterHeader(ctx=self.ctx, parent=view)
        view.setHorizontalHeader(header)
        header.init_filters(
            headers=model.raw_headers(),
            on_text_changed=lambda c, t: proxy.set_filter(c, t),
        )
        # Enable sorting and column reordering after replacing the header
        try:
            header.setSortIndicatorShown(True)
            header.setSectionsClickable(True)
            header.setSectionsMovable(True)
        except Exception as e:
            logger.log(
                VERBOSE,
                "TableViewer: header sort/sections: %s",
                e,
                exc_info=True,
            )
        view.setSortingEnabled(True)

        ctx = TableViewCtx(
            viewer=self,
            table=table,
            engine=engine,
            schema=schema,
            view=view,
            model=model,
            proxy=proxy,
            editing=False,
            extra_columns=list(default_extra) + list(user_extra),
        )
        self._views.append(ctx)
        for plg in self._plugins:
            try:
                plg.on_view_created(self, ctx)
            except Exception:
                logger.exception("ViewerPlugin.on_view_created failed")

        idx = self._tabs.addTab(view, label)
        self._tabs.setCurrentIndex(idx)
        self._apply_editing_state(ctx)
        if workspace_state:
            self.apply_workspace_state(ctx, workspace_state)

    def get_open_tables(self) -> List[Tuple[str, str]]:
        """Return (table_name, tab_label) for each open tab in order.

        Returns:
            List of (table name, tab label) for current tabs.
        """
        out: List[Tuple[str, str]] = []
        for i in range(self._tabs.count()):
            w = self._tabs.widget(i)
            label = self._tabs.tabText(i)
            for c in self._views:
                if c.view is w:
                    out.append((c.table, label))
                    break
        return out

    def _close_tab(self, idx: int) -> None:
        """Close a tab and drop its associated context.

        Args:
            idx: Tab index to close.
        """
        w = self._tabs.widget(idx)
        self._tabs.removeTab(idx)
        # Drop context for this widget
        self._views = [c for c in self._views if c.view is not w]
        if w is not None:
            w.deleteLater()
        if self._tabs.count() == 0:
            self.all_tabs_closed.emit()

    def clear_all_tabs(self) -> None:
        """Close all open tabs and clear the view contexts."""
        while self._tabs.count() > 0:
            self._close_tab(0)
        self._views = []

    def get_workspace_state_for_tab(self, ctx: TableViewCtx) -> Dict[str, Any]:
        """Return a serializable state dict for one tab (for workspace save).

        Includes column order, filters, sort, and user-added extra columns only
        (those with a string column name, not a callable).

        Args:
            ctx: The tab context.

        Returns:
            Dict with column_order, filters, sort_column, sort_direction,
            user_extra_columns.
        """
        model = ctx.model
        proxy = ctx.proxy
        header = ctx.view.horizontalHeader()
        headers = model.raw_headers()
        column_order = [
            str(headers[header.logicalIndex(vis)])
            for vis in range(header.count())
        ]
        filters = {
            str(headers[col]): str(proxy._filters.get(col, "") or "")
            for col in range(len(headers))
        }
        filters = {k: v for k, v in filters.items() if v}
        sort_logical = header.sortIndicatorSection()
        sort_column = str(headers[sort_logical]) if sort_logical >= 0 else None
        sort_direction = (
            "desc"
            if header.sortIndicatorOrder() == Qt.SortOrder.DescendingOrder
            else "asc"
        )
        user_extra_columns = [
            [str(fk), str(tt), str(tc)]
            for (fk, tt, tc) in ctx.extra_columns
            if not callable(tc)
        ]
        return {
            "column_order": column_order,
            "filters": filters,
            "sort_column": sort_column,
            "sort_direction": sort_direction,
            "user_extra_columns": user_extra_columns,
        }

    def apply_workspace_state(
        self, ctx: TableViewCtx, state: Dict[str, Any]
    ) -> None:
        """Apply a saved workspace state to a tab (column order, filters, sort).

        Args:
            ctx: The tab context (tab must already be created).
            state: Dict from get_workspace_state_for_tab.
        """
        model = ctx.model
        view = ctx.view
        header = ctx.view.horizontalHeader()
        if not isinstance(header, FilterHeader):
            return
        headers = model.raw_headers()
        headers_str = [str(h) for h in headers]
        column_order = state.get("column_order") or []
        if column_order and set(column_order) == set(headers_str):
            for target_visual, col_name in enumerate(column_order):
                try:
                    logical = headers_str.index(col_name)
                except ValueError:
                    continue
                current_visual = header.visualIndex(logical)
                if current_visual != target_visual:
                    header.moveSection(current_visual, target_visual)
        filters = state.get("filters") or {}
        for col_index, col_name in enumerate(headers_str):
            if col_name in filters and filters[col_name]:
                header.set_filter_value(col_index, filters[col_name])
        sort_column = state.get("sort_column")
        sort_direction = state.get("sort_direction") or "asc"
        if sort_column and sort_column in headers_str:
            try:
                logical = headers_str.index(sort_column)
                order = (
                    Qt.SortOrder.DescendingOrder
                    if sort_direction == "desc"
                    else Qt.SortOrder.AscendingOrder
                )
                view.sortByColumn(logical, order)
            except ValueError:
                pass

    def _ctx_for_view(self, view: "QTableView") -> Optional[TableViewCtx]:
        """Find the view context for a given QTableView, if any.

        Args:
            view: The QTableView to search.

        Returns:
            Matching TableViewCtx or None.
        """
        for c in self._views:
            if c.view is view:
                return c

        logger.error("TableViewer: no context found for view %s", id(view))
        return None

    def _tab_index_for_ctx(self, ctx: TableViewCtx) -> Optional[int]:
        """Return the tab index for the given context, or None.

        Args:
            ctx: The tab context.

        Returns:
            Tab index if found; None otherwise.
        """
        for i in range(self._tabs.count()):
            if self._tabs.widget(i) is ctx.view:
                return i
        return None

    def _apply_editing_state(self, ctx: TableViewCtx) -> None:
        """Apply the tab's editing flag to the view and tab icon.

        Sets view edit triggers, tab icon, and installs or removes the
        SqlColumnDelegate.

        Args:
            ctx: The tab context whose editing state to apply.
        """
        if ctx.editing:
            ctx.view.setEditTriggers(
                QAbstractItemView.DoubleClicked
                | QAbstractItemView.EditKeyPressed
            )
            try:
                icon = self.get_icon("edit_button")
                tab_idx = self._tab_index_for_ctx(ctx)
                if tab_idx is not None:
                    self._tabs.setTabIcon(tab_idx, icon)
            except Exception as e:
                logger.log(
                    VERBOSE,
                    "TableViewer: set tab icon: %s",
                    e,
                    exc_info=True,
                )
            is_editable = self._make_is_column_editable(ctx)
            delegate = SqlColumnDelegate(
                ctx.view,
                is_column_editable=is_editable,
                get_icon=self.get_icon,
                get_text=self.t,
            )
            ctx.view.setItemDelegate(delegate)
        else:
            ctx.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
            # Restore default delegate (paints NULL as italic grey centered).
            ctx.view.setItemDelegate(TableCellDelegate(ctx.view))
            tab_idx = self._tab_index_for_ctx(ctx)
            if tab_idx is not None:
                self._tabs.setTabIcon(tab_idx, QIcon())
        return None

    def _make_is_column_editable(
        self, ctx: TableViewCtx
    ) -> Callable[[str], bool]:
        """Return a callable that checks if a column is editable for this
        context.

        If no checks are registered, returns a callable that always returns
        True. Otherwise returns True if any registered check returns True.

        Args:
            ctx: The tab context (engine, schema, table).

        Returns:
            Callable(column_name: str) -> bool.
        """
        checks = self._column_editable_checks
        engine = ctx.engine
        schema = ctx.schema
        table = ctx.table

        def is_editable(column_name: str) -> bool:
            if not checks:
                return True
            for fn in checks:
                try:
                    if fn(engine, schema, table, column_name):
                        return True
                except Exception as e:
                    logger.log(
                        VERBOSE,
                        "TableViewer: column_editable_check %s: %s",
                        column_name,
                        e,
                        exc_info=True,
                    )
            return False

        return is_editable

    def _records_for_export(
        self, records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Convert record values to JSON- and YAML-serializable form.

        All keys are str; values are None, bool, int, float, or str so that
        both json.dumps and yaml.safe_dump work (SafeDumper rejects Decimal,
        bytes, UUID, etc.).

        Args:
            records: List of dicts from selected_records().

        Returns:
            List of dicts with scalar values only.
        """
        out: List[Dict[str, Any]] = []
        for row in records:
            normalized: Dict[str, Any] = {}
            for k, v in row.items():
                # Force built-in str so yaml.safe_dump accepts keys (rejects
                # str subclasses e.g. numpy.str_).
                key = str(k) if type(k) is not str else k
                if v is None:
                    normalized[key] = None
                elif isinstance(v, bool):
                    normalized[key] = bool(v)
                elif isinstance(v, int):
                    normalized[key] = int(v)
                elif isinstance(v, float):
                    normalized[key] = float(v)
                elif isinstance(v, (date, datetime)):
                    normalized[key] = v.isoformat()
                elif isinstance(v, str):
                    normalized[key] = str(v)
                else:
                    normalized[key] = str(v)
            out.append(normalized)
        return out

    def _copy_selected_as_csv(self, ctx: TableViewCtx) -> None:
        """Copy selected rows to clipboard as CSV.

        Args:
            ctx: The tab context.
        """
        records = ctx.selected_records()
        if not records:
            return
        export = self._records_for_export(records)
        headers = list(export[0].keys())
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=headers)
        writer.writeheader()
        for row in export:
            writer.writerow(
                {k: ("" if v is None else str(v)) for k, v in row.items()}
            )
        cb = QApplication.clipboard()
        if cb is not None:
            cb.setText(buf.getvalue())

    def _copy_selected_as_json(self, ctx: TableViewCtx) -> None:
        """Copy selected rows to clipboard as JSON.

        Args:
            ctx: The tab context.
        """
        records = ctx.selected_records()
        if not records:
            return
        export = self._records_for_export(records)
        text = json.dumps(export, indent=2)
        cb = QApplication.clipboard()
        if cb is not None:
            cb.setText(text)

    def _copy_selected_as_yaml(self, ctx: TableViewCtx) -> None:
        """Copy selected rows to clipboard as YAML.

        Args:
            ctx: The tab context.
        """
        records = ctx.selected_records()
        if not records:
            return
        export = self._records_for_export(records)
        text = yaml.safe_dump(export, default_flow_style=False)
        cb = QApplication.clipboard()
        if cb is not None:
            cb.setText(text)

    def _show_context_menu(self, view: "QTableView", point: QPoint) -> None:
        """Show a context menu built from Editing toggle, copy actions, and
        plugins.

        Args:
            view: The originating view.
            point: The local position for the menu.
        """
        ctx = self._ctx_for_view(view)
        if ctx is None:
            return
        menu = QMenu(view)
        if self._editing_allowed:
            ac_editing = QAction(
                self.t("table_viewer.editing", "Editing"), view
            )
            ac_editing.setCheckable(True)
            ac_editing.setChecked(ctx.editing)
            ac_editing.triggered.connect(
                lambda checked: self._on_editing_toggled(ctx, checked)
            )
            menu.addAction(ac_editing)
            menu.addSeparator()
        # Copy selected rows as CSV / JSON / YAML
        selected = ctx.selected_records()
        ac_csv = QAction(
            self.t("table_viewer.copy_as_csv", "Copy as CSV"),
            view,
        )
        ac_csv.setEnabled(bool(selected))
        ac_csv.triggered.connect(lambda: self._copy_selected_as_csv(ctx))
        menu.addAction(ac_csv)
        ac_json = QAction(
            self.t("table_viewer.copy_as_json", "Copy as JSON"),
            view,
        )
        ac_json.setEnabled(bool(selected))
        ac_json.triggered.connect(lambda: self._copy_selected_as_json(ctx))
        menu.addAction(ac_json)
        ac_yaml = QAction(
            self.t("table_viewer.copy_as_yaml", "Copy as YAML"),
            view,
        )
        ac_yaml.setEnabled(bool(selected))
        ac_yaml.triggered.connect(lambda: self._copy_selected_as_yaml(ctx))
        menu.addAction(ac_yaml)
        menu.addSeparator()
        ac_columns = QAction(
            self.t(
                "table_viewer.choose_visible_columns",
                "Choose visible columns…",
            ),
            view,
        )
        ac_columns.triggered.connect(
            lambda: self._open_column_visibility_dialog(ctx)
        )
        menu.addAction(ac_columns)
        # Stay-open submenu: Add columns from related table (FK joins)
        try:
            cache_key = (
                str(ctx.engine.url),
                ctx.schema or "",
                ctx.table,
            )
            if cache_key not in self._fk_columns_cache:
                self._fk_columns_cache[cache_key] = get_foreign_key_columns(
                    ctx.engine, ctx.schema, ctx.table
                )
            fk_list = self._fk_columns_cache[cache_key]
            if fk_list:
                menu.addSeparator()
                add_cols_menu = StayOpenMenu(view)
                add_cols_menu.setTitle(
                    self.t(
                        "table_viewer.add_columns_from_related",
                        "Add columns from related table",
                    )
                )
                current = set(ctx.extra_columns)
                for idx, (fk_col, target_table, target_cols) in enumerate(
                    fk_list
                ):
                    if idx > 0:
                        add_cols_menu.addSeparator()
                    ac_title = QAction("%s → %s" % (fk_col, target_table), view)
                    ac_title.setEnabled(False)
                    add_cols_menu.addAction(ac_title)
                    for target_col in target_cols:
                        ac = QAction(target_col, view)
                        ac.setCheckable(True)
                        triple = (fk_col, target_table, target_col)
                        ac.setChecked(triple in current)
                        ac.setData(triple)
                        add_cols_menu.addAction(ac)
                menu.addMenu(add_cols_menu)

                def on_add_cols_closed() -> None:
                    chosen = self._collect_join_choices_from_menu(add_cols_menu)
                    if chosen != ctx.extra_columns:
                        self._replace_model_with_joined_columns(ctx, chosen)

                add_cols_menu.aboutToHide.connect(on_add_cols_closed)
        except Exception:
            logger.debug(
                "Build FK join menu failed for %s",
                ctx.table,
                exc_info=True,
            )
        if self._plugins:
            menu.addSeparator()
        for plg in self._plugins:
            try:
                actions = plg.provide_actions(self, ctx)
                for a in actions:
                    menu.addAction(a)
            except Exception:
                logger.exception("ViewerPlugin.provide_actions failed")
        if menu.isEmpty():
            return
        vp = view.viewport()
        if vp is None:
            return
        menu.exec_(vp.mapToGlobal(point))

    def _open_column_visibility_dialog(self, ctx: TableViewCtx) -> None:
        """Open the column visibility dialog and apply chosen visibility.

        Reads current visibility from the header, shows the dialog, and on
        accept updates the view's horizontal header hidden state per section.

        Args:
            ctx: The tab context (model and view).
        """
        headers = ctx.model.raw_headers()
        header = ctx.view.horizontalHeader()
        initial_visible = [
            not header.isSectionHidden(i) for i in range(len(headers))
        ]
        dlg = ColumnVisibilityDialog(self, self.ctx, headers, initial_visible)
        if dlg.exec_() != QDialog.Accepted:
            return
        visibility = dlg.get_visibility()
        for i, vis in enumerate(visibility):
            if i < len(headers):
                header.setSectionHidden(i, not vis)

    def _replace_model_with_joined_columns(
        self,
        ctx: TableViewCtx,
        extra_columns: List[Tuple[str, str, str]],
    ) -> None:
        """Replace the tab model with one that includes the given join columns.

        Updates ctx.model and ctx.extra_columns, sets the proxy source, and
        re-initializes the filter header so column count matches.

        Args:
            ctx: The tab context.
            extra_columns: List of (fk_column, target_table, target_column).
        """
        limit = ctx.model.get_limit()
        new_model = SqlTableModel(
            engine=ctx.engine,
            schema=ctx.schema,
            table=ctx.table,
            limit=limit,
            extra_columns=extra_columns if extra_columns else None,
        )
        ctx.model = new_model
        ctx.extra_columns = list(extra_columns)
        ctx.proxy.setSourceModel(new_model)
        header = ctx.view.horizontalHeader()
        if isinstance(header, FilterHeader):
            header.init_filters(
                headers=new_model.raw_headers(),
                on_text_changed=lambda c, t: ctx.proxy.set_filter(c, t),
            )
        self._apply_editing_state(ctx)

    def _collect_join_choices_from_menu(
        self, menu: QMenu
    ) -> List[Tuple[str, str, str]]:
        """Collect (fk_col, target_table, target_col) from checkable actions.

        Recursively visits submenus. Uses Qt.UserRole for the triple.

        Args:
            menu: Menu that may contain checkable actions with UserRole data.

        Returns:
            List of triples for checked actions.
        """
        out: List[Tuple[str, str, str]] = []
        for ac in menu.actions():
            if ac.menu():
                out.extend(self._collect_join_choices_from_menu(ac.menu()))
            elif ac.isCheckable() and ac.isChecked():
                data = ac.data()
                if isinstance(data, (list, tuple)) and len(data) == 3:
                    out.append((data[0], data[1], data[2]))
        return out

    def _on_editing_toggled(self, ctx: TableViewCtx, checked: bool) -> None:
        """Handle the Editing menu checkbox toggle.

        If the user enables editing but the table has no primary key, show
        a toast, revert to not editing, and do not enable edit mode.

        Args:
            ctx: The tab context.
            checked: New state for editing mode.
        """
        if checked and not ctx.model._primary_key_names:
            from exdrf_qt.controls.toast import Toast

            msg = self.t(
                "table_viewer.no_primary_key",
                "This table has no primary key and cannot be edited.",
            )
            Toast.show_warning(self, msg)
            ctx.editing = False
            self._apply_editing_state(ctx)
            return
        ctx.editing = checked
        self._apply_editing_state(ctx)
