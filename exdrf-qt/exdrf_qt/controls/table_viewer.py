import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from PyQt5.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QPoint,
    QSortFilterProxyModel,
    Qt,
)
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
from sqlalchemy import MetaData, Table, select

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.filter_header import FilterHeader

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

    from exdrf_qt.context import QtContext

logger = logging.getLogger(__name__)
VERBOSE = 10


class SqlTableModel(QAbstractTableModel):
    """Simple read-only model loading rows from a table.

    Stores raw values internally; returns stringified values for display.

    Attributes:
        _headers: Column names, in column order.
        _rows: Table data cached as lists of raw values.
    """

    # Private attributes
    _headers: List[str]
    _rows: List[List[Any]]

    def __init__(
        self,
        *,
        engine: "Engine",
        schema: Optional[str],
        table: str,
        limit: int = 10000,
    ) -> None:
        """Initialize the table model and load initial data.

        Args:
            engine: SQLAlchemy engine to query.
            schema: Optional schema name.
            table: Table name to read.
            limit: Limit number of rows loaded initially.
        """
        super().__init__()
        self._headers: List[str] = []
        self._rows: List[List[Any]] = []
        self._load(engine, schema, table, limit)

    def rowCount(
        self, parent: QModelIndex = QModelIndex()
    ) -> int:  # noqa: N802
        """Number of rows in the table model.

        Args:
            parent: Required by Qt; unused for flat models.

        Returns:
            Number of records (may be truncated by limit).
        """
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(
        self, parent: QModelIndex = QModelIndex()
    ) -> int:  # noqa: N802
        """Number of columns.

        Args:
            parent: Required by Qt; unused.

        Returns:
            Number of columns.
        """
        return 0 if parent.isValid() else len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        """Cell data for requested index/role.

        Args:
            index: Model index.
            role: Qt role (Display/Edit).

        Returns:
            The textual representation for display/edit roles.
        """
        if not index.isValid():
            return None
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            try:
                val = self._rows[index.row()][index.column()]
                if val is None:
                    return ""
                return str(val)
            except Exception:
                return ""
        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        """Header values for the view.

        Args:
            section: Section index.
            orientation: Horizontal or Vertical.
            role: Qt role (Display role is used).
        """
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        else:
            return section + 1
        return None

    def raw_headers(self) -> List[str]:
        """Return a copy of the column headers list."""
        return list(self._headers)

    def raw_row(self, row: int) -> Optional[List[Any]]:
        """Return the raw row values for a given row index, if present."""
        if 0 <= row < len(self._rows):
            return self._rows[row]
        return None

    def _load(
        self, engine: "Engine", schema: Optional[str], table: str, limit: int
    ) -> None:
        """Load headers and initial rows into memory.

        Args:
            engine: SQLAlchemy engine.
            schema: Optional schema.
            table: Table name.
            limit: Row limit for the preview.
        """
        logger.log(
            VERBOSE,
            "SqlTableModel: load table=%s schema=%s limit=%s",
            table,
            schema,
            limit,
        )
        meta = MetaData()
        t = Table(table, meta, autoload_with=engine, schema=schema)
        self._headers = [c.name for c in t.columns]
        stmt = select(t)
        if limit > 0:
            stmt = stmt.limit(limit)
        with engine.connect() as conn:
            rs = conn.execute(stmt)
            for row in rs:
                mapping = row._mapping  # SQLAlchemy RowMapping view
                self._rows.append([mapping[h] for h in self._headers])
        logger.log(
            VERBOSE,
            "SqlTableModel: loaded rows=%d cols=%d",
            len(self._rows),
            len(self._headers),
        )


class ColumnFilterProxy(QSortFilterProxyModel):
    """Proxy model that applies per-column substring filters (case-insensitive).

    Attributes:
        _filters: Map from column index to current filter text.
    """

    # Private attributes
    _filters: Dict[int, str]

    def __init__(self) -> None:
        """Initialize the proxy model and filtering behavior."""
        super().__init__()
        self._filters: Dict[int, str] = {}
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setDynamicSortFilter(True)

    def set_filter(self, column: int, text: str) -> None:
        """Set a filter string for a given column.

        Args:
            column: Column index.
            text: Substring to match (case-insensitive).
        """
        logger.log(
            VERBOSE,
            "ColumnFilterProxy: set_filter col=%d text=%r",
            column,
            text,
        )
        self._filters[column] = text or ""
        self.invalidateFilter()

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        """Forward header data from the source model so the header shows labels.

        Args:
            section: Section index.
            orientation: Horizontal or Vertical.
            role: Qt role (Display role is used for labels).

        Returns:
            Header label from source model, or None.
        """
        src = self.sourceModel()
        if src is not None:
            return src.headerData(section, orientation, role)
        return None

    def filterAcceptsRow(
        self, source_row: int, source_parent: QModelIndex
    ) -> bool:  # noqa: N802
        """Decide whether a source row matches all active column filters.

        Args:
            source_row: Source model row.
            source_parent: Source parent index.

        Returns:
            True if row matches all filters; False otherwise.
        """
        model = self.sourceModel()
        if model is None:
            return True
        for col, pattern in self._filters.items():
            if not pattern:
                continue
            idx = model.index(source_row, col, source_parent)
            text = str(model.data(idx, Qt.ItemDataRole.DisplayRole) or "")
            if pattern.lower() not in text.lower():
                return False
        return True

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:  # type: ignore[override]
        """Sort numbers numerically when possible, fallback to text compare.

        Args:
            left: Left index in source model.
            right: Right index in source model.

        Returns:
            True if left < right according to numeric-aware ordering.
        """
        model = self.sourceModel()
        if model is None:
            return super().lessThan(left, right)

        lv = model.data(left, Qt.ItemDataRole.DisplayRole)
        rv = model.data(right, Qt.ItemDataRole.DisplayRole)

        def _to_num(val):
            if val is None:
                return None
            s = str(val).strip()
            if not s:
                return None
            try:
                # Try integer first for stable ordering
                return int(s)
            except Exception:
                try:
                    return float(s)
                except Exception:
                    return None

        ln = _to_num(lv)
        rn = _to_num(rv)

        if ln is not None and rn is not None:
            return ln < rn

        # Fallback: case-insensitive text compare
        ls = ("" if lv is None else str(lv)).lower()
        rs = ("" if rv is None else str(rv)).lower()
        return ls < rs


@dataclass(slots=True)
class TableViewCtx:
    """Context object with references for one open table tab.

    Attributes:
        viewer: Viewer instance that owns the tab.
        table: The opened table name.
        engine: The engine used to read.
        schema: Optional schema in use.
        view: The QTableView displaying the table.
        model: The underlying data model.
        proxy: The active filter proxy for the view.
    """

    viewer: "TableViewer"
    table: str
    engine: "Engine"
    schema: Optional[str]
    view: "QTableView"
    model: "SqlTableModel"
    proxy: "ColumnFilterProxy"

    def selected_records(self) -> List[Dict[str, Any]]:
        """Return raw dict rows for current row selection.

        Returns:
            List of dicts mapping column name to raw value.
        """
        sel = self.view.selectionModel()
        if not sel:
            return []
        headers = self.model.raw_headers()
        out: List[Dict[str, Any]] = []
        for prx_idx in sel.selectedRows():
            src_idx = self.proxy.mapToSource(prx_idx)
            raw = self.model.raw_row(src_idx.row())
            if raw is None:
                continue
            out.append({headers[i]: raw[i] for i in range(len(headers))})
        return out


class ViewerPlugin:
    """Plugin interface for TableViewer.

    Subclasses override methods to contribute actions and be notified when a
    view is created.
    """

    def provide_actions(
        self, viewer: "TableViewer", ctx: "TableViewCtx"
    ) -> List[QAction]:
        """Return actions for a given view context.

        Args:
            viewer: Hosting viewer.
            ctx: View context for which to provide actions.

        Returns:
            List of actions to add to the context menu.
        """
        return []

    def on_view_created(
        self, viewer: "TableViewer", ctx: "TableViewCtx"
    ) -> None:
        """Hook called when a new view is created.

        Args:
            viewer: Hosting viewer.
            ctx: View context that was created.
        """
        return None


class TableViewer(QWidget, QtUseContext):
    """Generic tabbed table viewer with per-column filters and plugins.

    Attributes:
        ctx: The application context.

    Private Attributes:
        _tabs: The QTabWidget hosting open tables.
        _plugins: Installed viewer plugins.
        _views: Context list for each open tab.
    """

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
        self._plugins: List[ViewerPlugin] = []
        self._views: List[TableViewCtx] = []

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
        self, *, engine: "Engine", schema: Optional[str], table: str
    ) -> None:
        """Open a table in a new tab.

        Args:
            engine: Engine to read from.
            schema: Optional schema name.
            table: Table name.
        """
        logger.log(
            VERBOSE, "TableViewer: open_table table=%s schema=%s", table, schema
        )
        model = SqlTableModel(engine=engine, schema=schema, table=table)
        proxy = ColumnFilterProxy()
        proxy.setSourceModel(model)

        # Create and configure view
        view = QTableView(self)
        view.setModel(proxy)
        hh: QHeaderView = view.horizontalHeader()
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
        except Exception:
            pass
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

        idx = self._tabs.addTab(view, table)
        self._tabs.setCurrentIndex(idx)

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

    def _ctx_for_view(self, view: "QTableView") -> Optional["TableViewCtx"]:
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
