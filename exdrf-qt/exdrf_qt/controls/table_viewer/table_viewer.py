"""Tabbed table viewer widget with per-column filters and plugins."""

import logging
from typing import TYPE_CHECKING, List, Optional, Tuple

from PyQt5.QtCore import QPoint, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView,
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
        all_tabs_closed: Emitted when the last tab is closed (tab count becomes 0).

    Private Attributes:
        _tabs: The QTabWidget hosting open tables.
        _plugins: Installed viewer plugins.
        _views: Context list for each open tab.
    """

    all_tabs_closed = pyqtSignal()

    # Public attributes
    ctx: "QtContext"

    # Private attributes
    _tabs: QTabWidget
    _plugins: List[ViewerPlugin]
    _views: List[TableViewCtx]

    def __init__(self, ctx, parent: Optional[QWidget] = None) -> None:
        """Initialize the viewer widget.

        Args:
            ctx: Application context.
            parent: Optional parent widget.
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

    def add_plugin(self, plugin: ViewerPlugin) -> None:
        """Install a plugin that contributes actions and hooks.

        Args:
            plugin: The plugin instance to add.
        """
        self._plugins.append(plugin)
        logger.log(
            VERBOSE, "TableViewer: plugin added %s", type(plugin).__name__
        )

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
                1,
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
        )
        self._views.append(ctx)
        for plg in self._plugins:
            try:
                plg.on_view_created(self, ctx)
            except Exception:
                logger.exception("ViewerPlugin.on_view_created failed")

        idx = self._tabs.addTab(view, label)
        self._tabs.setCurrentIndex(idx)

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

    def _show_context_menu(self, view: "QTableView", point: QPoint) -> None:
        """Show a context menu built from plugins for the given view.

        Args:
            view: The originating view.
            point: The local position for the menu.
        """
        ctx = self._ctx_for_view(view)
        if ctx is None:
            return
        menu = QMenu(view)
        # Plugin actions first
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
