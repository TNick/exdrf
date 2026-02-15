"""Tabbed table viewer widget with per-column filters and plugins."""

import logging
from typing import TYPE_CHECKING, Callable, List, Optional, Tuple

from PyQt5.QtCore import QPoint, Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
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
from exdrf_qt.controls.table_viewer.sql_column_delegate import (
    SqlColumnDelegate,
    TableCellDelegate,
)
from exdrf_qt.controls.table_viewer.sql_table_model import SqlTableModel
from exdrf_qt.controls.table_viewer.table_view_ctx import TableViewCtx
from exdrf_qt.controls.table_viewer.viewer_plugin import ViewerPlugin

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

    from exdrf_qt.context import QtContext

logger = logging.getLogger(__name__)
VERBOSE = 10


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
    ) -> None:
        """Open a table in a new tab.

        Args:
            engine: Engine to read from.
            schema: Optional schema name.
            table: Table name (used for loading data).
            tab_label: Optional label for the tab; if None, uses table.
        """
        label = tab_label if tab_label is not None else table
        logger.log(
            VERBOSE, "TableViewer: open_table table=%s schema=%s", table, schema
        )
        model = SqlTableModel(engine=engine, schema=schema, table=table)
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
        # Ensure sorting is enabled after replacing the header
        try:
            header.setSortIndicatorShown(True)
            header.setSectionsClickable(True)
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

    def _show_context_menu(self, view: "QTableView", point: QPoint) -> None:
        """Show a context menu built from Editing toggle and plugins.

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
