"""Database viewer with connection chooser, table list, autocompleter and
stacked view.
"""

import logging
from typing import TYPE_CHECKING, List, Optional, cast

from exdrf_al.connection import DbConn
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCompleter,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import inspect

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.seldb.choose_db import ChooseDb
from exdrf_qt.controls.table_viewer.table_viewer import TableViewer

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

    from exdrf_qt.context import QtContext

logger = logging.getLogger(__name__)

# Stack indices
PAGE_LIST = 0
PAGE_VIEWER = 1

# If user adds more than this many tables at once, show a confirmation dialog.
MAX_TABLES_WITHOUT_CONFIRM = 6


class DbViewer(QWidget, QtUseContext):
    """Database viewer with connection chooser and table list/autocompleter.

    When no tables are open, shows a full-table list with checkboxes and OK.
    When tables are open, shows the tabbed TableViewer. A stacked widget
    switches between the list page and the viewer page. Same table can be
    added multiple times (distinct tabs). Connection is selected via a
    ChooseDb at the top; changing connection refreshes the table list and
    clears open tabs.

    Attributes:
        ctx: The application context.

    Private Attributes:
        _lbl_connection: Label shown next to the connection chooser.
        _chooser: Database connection chooser.
        _btn_manage_connection: Button to open the database settings dialog.
        _engine: Current engine; None if no connection selected.
        _schema: Current schema; None if no connection or SQLite.
        _table_names: Cached list of table names for current engine/schema.
        _stack: Stacked widget (list page index 0, viewer page index 1).
        _list_page: Widget with table list and OK button.
        _list_filter_line: Line edit to filter the table list by name
            (no completer).
        _list_widget: QListWidget with checkable table names.
        _viewer: Embedded TableViewer.
        _top_bar_widget: Widget containing table line edit and Add / Add tables…
            buttons; visible only when the tabbed viewer page is shown.
        _top_line: QLineEdit for table name with completer.
        _btn_add: Add button.
        _btn_show_list: Button to show the table list again.
        _btn_close_tabs_list: On list page, button to switch back to the tabbed
            viewer; visible only when there are open tabs.
    """

    ctx: "QtContext"

    _lbl_connection: QLabel
    _chooser: ChooseDb
    _btn_manage_connection: QPushButton
    _engine: Optional["Engine"]
    _schema: Optional[str]
    _table_names: List[str]
    _stack: QStackedWidget
    _list_page: QWidget
    _list_filter_line: QLineEdit
    _list_widget: QListWidget
    _viewer: TableViewer
    _top_bar_widget: QWidget
    _top_line: QLineEdit
    _btn_add: QPushButton
    _btn_show_list: QPushButton
    _btn_close_tabs_list: QPushButton

    def __init__(
        self,
        ctx: "QtContext",
        *,
        parent: Optional[QWidget] = None,
        initial_cfg_id: Optional[str] = None,
    ) -> None:
        """Initialize the database viewer.

        Args:
            ctx: Application context (for TableViewer, ChooseDb, translations).
            parent: Optional parent widget.
            initial_cfg_id: Optional DB config id to select initially.
        """
        super().__init__(parent)
        self.ctx = ctx
        self._engine = None
        self._schema = None
        self._table_names = []

        # Connection chooser with label
        self._lbl_connection = QLabel(
            self.t("db_viewer.connection", "Connection:"), self
        )
        self._chooser = ChooseDb(ctx=ctx, parent=self)
        self._chooser.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._chooser.populate_db_connections()
        if initial_cfg_id:
            model = self._chooser.model()
            if hasattr(model, "find_config_index"):
                idx = model.find_config_index(initial_cfg_id)
                if idx is not None:
                    self._chooser.setCurrentIndex(idx.row())
        self._chooser.currentIndexChanged.connect(self._on_connection_changed)

        self._btn_manage_connection = QPushButton(
            self.get_icon("wrench"), self.t("db_viewer.manage", "Manage"), self
        )
        self._btn_manage_connection.clicked.connect(
            self._on_manage_connection_clicked
        )

        # Top bar: label, line edit with completer, Add, Show list (visible only
        # when tabbed viewer is shown)
        self._top_bar_widget = QWidget(self)
        top_bar = QHBoxLayout(self._top_bar_widget)
        top_bar.setContentsMargins(0, 0, 0, 4)
        lbl = QLabel(self.t("db_viewer.table", "Table:"), self._top_bar_widget)
        self._top_line = QLineEdit(self._top_bar_widget)
        self._top_line.setPlaceholderText(
            self.t("db_viewer.table_placeholder", "Type or select table name")
        )
        completer = QCompleter(self._table_names)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._top_line.setCompleter(completer)

        self._btn_add = QPushButton(
            self.get_icon("plus"),
            self.t("db_viewer.add", " Add"),
            self._top_bar_widget,
        )
        self._btn_add.clicked.connect(self._on_add_clicked)

        self._btn_show_list = QPushButton(
            self.get_icon("application_view_list"),
            self.t("db_viewer.show_list", "Choose tables…"),
            self._top_bar_widget,
        )
        self._btn_show_list.clicked.connect(self._on_show_list_clicked)

        top_bar.addWidget(lbl)
        top_bar.addWidget(self._top_line, 1)
        top_bar.addWidget(self._btn_add)
        top_bar.addWidget(self._btn_show_list)

        # List page: invite label, checkable list of all tables, Add button
        # centered
        self._list_page = QWidget(self)
        list_ly = QVBoxLayout(self._list_page)
        list_ly.setContentsMargins(0, 0, 0, 0)
        lbl_invite = QLabel(
            self.t(
                "db_viewer.list_invite",
                "Select the tables you want to open, then click Add.",
            ),
            self._list_page,
        )
        list_ly.addWidget(lbl_invite)
        filter_row = QHBoxLayout()
        filter_row.setContentsMargins(0, 0, 0, 2)
        lbl_filter = QLabel(
            self.t("db_viewer.filter", "Filter:"), self._list_page
        )
        self._list_filter_line = QLineEdit(self._list_page)
        self._list_filter_line.setClearButtonEnabled(True)
        self._list_filter_line.textChanged.connect(self._apply_list_filter)
        filter_row.addWidget(lbl_filter)
        filter_row.addWidget(self._list_filter_line, 1)
        list_ly.addLayout(filter_row)
        self._list_widget = QListWidget(self._list_page)
        self._list_widget.setSelectionMode(QListWidget.NoSelection)
        self._list_widget.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self._list_widget.customContextMenuRequested.connect(
            self._on_list_context_menu
        )
        list_ly.addWidget(self._list_widget)

        self._btn_close_tabs_list = QPushButton(
            self.t("db_viewer.show_tabs", "Cancel"),
            self._list_page,
        )
        self._btn_close_tabs_list.clicked.connect(self._on_back_to_tabs)

        btn_add_list = QPushButton(
            self.t("db_viewer.add", " Add"), self._list_page
        )
        btn_add_list.setIcon(self.get_icon("plus"))
        btn_add_list.clicked.connect(self._on_list_ok_clicked)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(btn_add_list)
        btn_row.addWidget(self._btn_close_tabs_list)
        btn_row.addStretch(1)
        list_ly.addLayout(btn_row)

        # Viewer page: embedded TableViewer
        self._viewer = TableViewer(ctx=ctx, parent=self)
        self._viewer.all_tabs_closed.connect(self._on_all_tabs_closed)

        # Stack
        self._stack = QStackedWidget(self)
        self._stack.addWidget(self._list_page)
        self._stack.addWidget(self._viewer)

        root = QVBoxLayout(self)
        root.setContentsMargins(2, 2, 2, 2)
        conn_row = QHBoxLayout()
        conn_row.addWidget(self._lbl_connection)
        conn_row.addWidget(self._chooser, 1)
        conn_row.addWidget(self._btn_manage_connection)
        root.addLayout(conn_row)
        root.addWidget(self._top_bar_widget)
        root.addWidget(self._stack)

        # Apply initial connection and refresh UI (after all widgets exist).
        self._on_connection_changed()

    def _current_config(self) -> Optional[dict]:
        """Return the selected DB config from the chooser, or None."""
        idx = self._chooser.currentIndex()
        if idx < 0:
            return None
        return self._chooser.itemData(idx)

    def _on_manage_connection_clicked(self) -> None:
        """Open the database settings dialog and refresh the chooser after."""
        cfg = self._current_config()
        prev_id = cfg.get("id") if cfg else None
        try:
            from exdrf_qt.controls.seldb.sel_db import SelectDatabaseDlg

            dlg = SelectDatabaseDlg(
                ctx=self.ctx, parent=self, show_transfer_button=False
            )
            dlg.exec_()
        except Exception as e:
            logger.error(
                "DbViewer: failed to open database settings: %s",
                e,
                exc_info=True,
            )
            return
        self._chooser.populate_db_connections()
        if prev_id:
            model = self._chooser.model()
            if hasattr(model, "find_config_index"):
                idx = model.find_config_index(prev_id)
                if idx is not None:
                    self._chooser.setCurrentIndex(idx.row())
        self._on_connection_changed()

    def _on_connection_changed(self) -> None:
        """Update engine/schema from chooser; keep open tabs that exist in
        new DB.
        """
        cfg = self._current_config()
        if not cfg:
            self._engine = None
            self._schema = None
            self._table_names = []
            self._viewer.clear_all_tabs()
            self._refresh_table_list()
            self._stack.setCurrentIndex(PAGE_LIST)
            self._update_ui_state()
            return
        try:
            open_tables = self._viewer.get_open_tables()
            current_idx = self._viewer._tabs.currentIndex()
            active_table = (
                open_tables[current_idx][0]
                if 0 <= current_idx < len(open_tables)
                else None
            )
            cn = DbConn(
                c_string=cfg.get("c_string", ""),
                schema=cfg.get("schema", "public") or "public",
            )
            engine = cn.connect()
            self._engine = engine
            self._schema = cn.schema
            self._table_names = self._fetch_table_names()
            self._viewer.clear_all_tabs()
            self._refresh_table_list()
            active_new_idx: Optional[int] = None
            new_idx = 0
            for table, tab_label in open_tables:
                if table not in self._table_names:
                    continue
                try:
                    self._viewer.open_table(
                        engine=self._engine,
                        schema=self._schema,
                        table=table,
                        tab_label=tab_label,
                    )
                    if table == active_table:
                        active_new_idx = new_idx
                    new_idx += 1
                except Exception as e:
                    logger.debug(
                        "DbViewer: failed to reopen table %s: %s",
                        table,
                        e,
                        exc_info=True,
                    )
            if self._viewer._tabs.count() > 0:
                self._stack.setCurrentIndex(PAGE_VIEWER)
                self._viewer._tabs.setCurrentIndex(
                    active_new_idx if active_new_idx is not None else 0
                )
        except Exception as e:
            logger.error("DbViewer: connection failed: %s", e, exc_info=True)
            self._engine = None
            self._schema = None
            self._table_names = []
            self.show_error(
                self.t(
                    "db_viewer.connect_failed",
                    "Failed to connect: {err}",
                    err=str(e),
                ),
                title=self.t("cmn.error", "Error"),
            )
        self._update_ui_state()

    def _refresh_table_list(self) -> None:
        """Repopulate the list widget and completer from _table_names."""
        self._list_widget.clear()
        for name in sorted(self._table_names):
            item = QListWidgetItem(name)
            item.setFlags(
                cast(
                    Qt.ItemFlags,
                    Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled,
                )
            )
            item.setCheckState(Qt.CheckState.Unchecked)
            self._list_widget.addItem(item)
        completer = QCompleter(self._table_names)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._top_line.setCompleter(completer)
        self._apply_list_filter()

    def _apply_list_filter(self) -> None:
        """Show or hide list items based on the filter line (case-insensitive)."""
        needle = self._list_filter_line.text().strip().lower()
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            if not needle:
                item.setHidden(False)
            else:
                item.setHidden(needle not in item.text().lower())

    def _fetch_table_names(self) -> List[str]:
        """Return list of table names for the current engine and schema."""
        if self._engine is None:
            return []
        try:
            ins = inspect(self._engine)
            schema_arg = (
                self._schema if self._engine.dialect.name != "sqlite" else None
            )
            names = ins.get_table_names(schema=schema_arg)
            return names or []
        except Exception as e:
            logger.error(
                "DbViewer: failed to get table names: %s", e, exc_info=True
            )
            return []

    def _on_add_clicked(self) -> None:
        """Add the table from the line edit as a new tab."""
        name = self._top_line.text().strip()
        if not name or self._engine is None:
            return
        self._open_table_and_show_viewer(name)
        self._top_line.clear()

    def _on_list_context_menu(self, position) -> None:
        """Show context menu for the table list (check all / none / invert)."""
        menu = QMenu(self)
        menu.addAction(
            self.t("db_viewer.check_all", "Check all"),
            self._check_all_tables,
        )
        menu.addAction(
            self.t("db_viewer.check_none", "Check none"),
            self._check_none_tables,
        )
        menu.addAction(
            self.t("db_viewer.check_invert", "Invert check"),
            self._invert_table_checks,
        )
        menu.exec_(self._list_widget.mapToGlobal(position))

    def _check_all_tables(self) -> None:
        """Set all table list items to checked."""
        for i in range(self._list_widget.count()):
            self._list_widget.item(i).setCheckState(Qt.CheckState.Checked)

    def _check_none_tables(self) -> None:
        """Set all table list items to unchecked."""
        for i in range(self._list_widget.count()):
            self._list_widget.item(i).setCheckState(Qt.CheckState.Unchecked)

    def _invert_table_checks(self) -> None:
        """Toggle check state of every table list item."""
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            item.setCheckState(
                Qt.CheckState.Unchecked
                if item.checkState() == Qt.CheckState.Checked
                else Qt.CheckState.Checked
            )

    def _on_list_ok_clicked(self) -> None:
        """Open all checked tables and switch to the viewer page."""
        if self._engine is None:
            return

        checked = []
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                checked.append(item.text())

        if len(checked) > MAX_TABLES_WITHOUT_CONFIRM:
            reply = QMessageBox.question(
                self,
                self.t("db_viewer.many_tables.title", "Open many tables?"),
                self.t(
                    "db_viewer.many_tables.msg",
                    "You are about to open {n} tables. Continue?",
                    n=len(checked),
                ),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                table = item.text()
                tab_label = self._next_tab_label(table)
                self._viewer.open_table(
                    engine=self._engine,
                    schema=self._schema,
                    table=table,
                    tab_label=tab_label,
                )
                item.setCheckState(Qt.CheckState.Unchecked)
        self._stack.setCurrentIndex(PAGE_VIEWER)
        self._update_ui_state()

    def _on_show_list_clicked(self) -> None:
        """Switch to the table list page so the user can add more tables."""
        self._stack.setCurrentIndex(PAGE_LIST)
        self._update_ui_state()

    def _on_back_to_tabs(self) -> None:
        """Switch back to the tabbed viewer from the list page."""
        self._stack.setCurrentIndex(PAGE_VIEWER)
        self._update_ui_state()

    def _on_all_tabs_closed(self) -> None:
        """Switch back to the table list when the last tab is closed."""
        self._stack.setCurrentIndex(PAGE_LIST)
        self._update_ui_state()

    def _next_tab_label(self, table: str) -> str:
        """Return a unique tab label for the given table name."""
        labels = []
        for i in range(self._viewer._tabs.count()):
            labels.append(self._viewer._tabs.tabText(i))
        if table not in labels:
            return table
        n = 2
        while True:
            candidate = "%s (%d)" % (table, n)
            if candidate not in labels:
                return candidate
            n += 1

    def _open_table_and_show_viewer(self, table: str) -> None:
        """Open one table in the viewer and switch to viewer page if needed."""
        if self._engine is None:
            return
        try:
            tab_label = self._next_tab_label(table)
            self._viewer.open_table(
                engine=self._engine,
                schema=self._schema,
                table=table,
                tab_label=tab_label,
            )
            if self._stack.currentIndex() == PAGE_LIST:
                self._stack.setCurrentIndex(PAGE_VIEWER)
            self._update_ui_state()
        except Exception as e:
            logger.error(
                "DbViewer: failed to open table %s: %s", table, e, exc_info=True
            )
            self.show_error(
                self.t(
                    "db_viewer.open_failed",
                    "Failed to open table «{name}»: {err}",
                    name=table,
                    err=str(e),
                ),
                title=self.t("cmn.error", "Error"),
            )

    def _update_ui_state(self) -> None:
        """Show/hide top bar, list close button, enable/disable Add and
        how list.
        """
        on_viewer_page = self._stack.currentIndex() == PAGE_VIEWER
        self._top_bar_widget.setVisible(on_viewer_page)
        has_open_tabs = self._viewer._tabs.count() > 0
        self._btn_close_tabs_list.setVisible(
            not on_viewer_page and has_open_tabs
        )
        has_conn = self._engine is not None
        self._btn_add.setEnabled(has_conn)
        self._btn_show_list.setEnabled(has_conn and on_viewer_page)

    def add_plugin(self, plugin) -> None:
        """Forward plugin registration to the embedded TableViewer.

        Args:
            plugin: ViewerPlugin instance to add.
        """
        self._viewer.add_plugin(plugin)

    def set_initial_connection(self, cfg_id: Optional[str]) -> None:
        """Set the connection chooser to the given config id if present.

        Call after construction to preselect a connection (e.g. from db_tools).

        Args:
            cfg_id: DB config id to select, or None to leave as-is.
        """
        if not cfg_id:
            return
        model = self._chooser.model()
        if not hasattr(model, "find_config_index"):
            return
        idx = model.find_config_index(cfg_id)
        if idx is not None:
            self._chooser.setCurrentIndex(idx.row())
            self._on_connection_changed()
