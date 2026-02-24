"""Main transfer widget: two-pane DB transfer with table list and viewer."""

import logging
from typing import TYPE_CHECKING, List, Optional, cast

from exdrf_al.connection import DbConn
from PyQt5.QtCore import (
    QItemSelectionModel,
    QPoint,
    QSortFilterProxyModel,
    Qt,
    QTimer,
)
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.filter_header import FilterHeader
from exdrf_qt.controls.seldb.choose_db import ChooseDb
from exdrf_qt.controls.table_viewer import TableViewer
from exdrf_qt.controls.transfer.numeric_sort_proxy import NumericSortProxy
from exdrf_qt.controls.transfer.tables_model import TablesModel
from exdrf_qt.controls.transfer.transfer_selected_plugin import (
    TransferSelectedPlugin,
)
from exdrf_qt.controls.transfer.transfer_worker import TransferWorker
from exdrf_qt.plugins import exdrf_qt_pm
from exdrf_qt.utils.plugins import get_hook_safely, safe_hook_call

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext

logger = logging.getLogger(__name__)
VERBOSE = 1


class TransferWidget(QWidget, QtUseContext):
    """Widget to transfer data from one DB connection to another.

    Layout: two panes (source on left, destination on right). Each pane has a
    database chooser and a lazy-count tables list. Right-click on the source
    list enables full-table Transfer and View; both panes support View via a
    reusable TableViewer. Selected-row transfers are available inside the
    viewer via a plugin.

    Attributes:
        ctx: The application context.

    Private Attributes:
        _src_conn: Current source connection.
        _dst_conn: Current destination connection.
        _src_view_win: Source TableViewer window if open.
        _dst_view_win: Destination TableViewer window if open.
        _spin_chunk: Spin control holding the current chunk size.
        _src_db: Source DB chooser.
        _dst_db: Destination DB chooser.
        _src_model: Source tables model.
        _dst_model: Destination tables model.
        _src_view: Source tables view.
        _dst_view: Destination tables view.
    """

    # Public attributes
    ctx: "QtContext"

    # Private attributes
    _src_conn: Optional["DbConn"]
    _dst_conn: Optional["DbConn"]
    _src_view_win: TableViewer = None  # type: ignore
    _dst_view_win: TableViewer = None  # type: ignore
    _spin_chunk: "QSpinBox"
    _src_db: "ChooseDb"
    _dst_db: "ChooseDb"
    _btn_settings: "QPushButton"
    _btn_bootstrap: "QPushButton"
    _src_model: TablesModel
    _dst_model: TablesModel
    _src_view: "QTableView"
    _dst_view: "QTableView"
    _full_worker: Optional["TransferWorker"]
    _sync_scroll: bool
    _sync_in_progress: bool

    def __init__(self, ctx, parent: Optional["QWidget"] = None) -> None:
        """Initialize the transfer widget.

        Args:
            ctx: The application context.
            parent: Optional Qt parent widget.
        """
        super().__init__(parent)
        self.ctx = ctx

        # Connections for both sides
        self._src_conn: Optional[DbConn] = None
        self._dst_conn: Optional[DbConn] = None

        # One count-error toast per connection selection (cleared when
        # selection changes)
        self._src_count_error_shown: bool = False
        self._dst_count_error_shown: bool = False

        # Build UI controls and top toolbar
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(2, 2, 2, 2)
        top_bar.setSpacing(6)
        lbl_chunk = QLabel(self.t("tr.chunk", "Transfer chunk size:"), self)
        self._spin_chunk = QSpinBox(self)
        self._spin_chunk.setRange(1, 50000)
        self._spin_chunk.setSingleStep(100)
        self._spin_chunk.setValue(1000)
        top_bar.addWidget(lbl_chunk)
        top_bar.addWidget(self._spin_chunk)

        # Settings button opens the DB manager dialog
        self._btn_settings = QPushButton(
            self.t("tr.settings", "Settings"), self
        )
        self._btn_settings.setIcon(self.get_icon("edit_button"))
        self._btn_settings.clicked.connect(self._on_open_settings)

        # Bootstrap button applies to the destination connection
        self._btn_bootstrap = QPushButton(
            self.t("tr.bootstrap", "Bootstrap"), self
        )
        self._btn_bootstrap.setIcon(self.get_icon("sitemap_application_blue"))
        self._btn_bootstrap.clicked.connect(self._on_bootstrap_dst)

        top_bar.addWidget(self._btn_settings)
        top_bar.addWidget(self._btn_bootstrap)
        top_bar.addStretch(1)

        # Create the two-pane splitter
        split = QSplitter(Qt.Orientation.Horizontal, self)
        l_side = self._build_side(is_src=True)
        r_side = self._build_side(is_src=False)
        split.addWidget(l_side)
        split.addWidget(r_side)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 1)

        # Compose the root layout
        root = QVBoxLayout(self)
        root.setContentsMargins(2, 2, 2, 2)
        root.addLayout(top_bar)
        root.addWidget(split)
        self.setLayout(root)
        logger.log(VERBOSE, "TransferWidget: UI initialized")

        # Populate database choosers
        self._src_db.populate_db_connections()
        self._dst_db.populate_db_connections()

        # Select newest connection for source on startup, clear destination
        self._select_newest_for_source()
        self._clear_destination()

        # Initial refresh and sync counts
        self._src_model.refresh()
        self._dst_model.refresh()
        self._run_counts_sync("src")
        self._run_counts_sync("dst")

        # Track running full-table transfer worker (if any)
        self._full_worker = None
        logger.log(VERBOSE, "TransferWidget: initial state ready")

        # Sync scroll (disabled by default)
        self._sync_scroll = False
        self._sync_in_progress = False

    # UI construction helpers
    def _build_side(self, *, is_src: bool) -> QWidget:
        """Construct one side of the UI (source or destination).

        Args:
            is_src: True for the source pane, False for destination.

        Returns:
            The constructed side widget.
        """
        w = QWidget(self)
        ly = QVBoxLayout(w)
        ly.setContentsMargins(2, 2, 2, 2)
        ly.setSpacing(4)

        db = ChooseDb(ctx=self.ctx, parent=w)
        db.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        ly.addWidget(db)

        model = TablesModel(ctx=self.ctx, side="src" if is_src else "dst")
        view = QTableView(w)
        proxy = NumericSortProxy(view)
        proxy.setSourceModel(model)
        proxy.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        proxy.setDynamicSortFilter(True)
        view.setModel(proxy)
        view.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        # Install per-column filter header
        header = FilterHeader(ctx=self.ctx, parent=view)
        view.setHorizontalHeader(header)
        header.init_filters(
            headers=[
                self.t("tr.tables.name", "Table"),
                self.t("tr.tables.counts", "Rows"),
            ],
            on_text_changed=lambda c, t: proxy.set_filter(c, t),
        )
        try:
            header.setSortIndicatorShown(True)
            header.setSectionsClickable(True)
        except Exception as e:
            logger.log(VERBOSE, "TransferWidget: %s", e, exc_info=True)

        view.setSortingEnabled(True)
        view.setSelectionBehavior(QAbstractItemView.SelectRows)
        view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        view.setAlternatingRowColors(True)
        view.setSortingEnabled(True)
        view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        view.customContextMenuRequested.connect(
            lambda p, s=self, v=view, src=is_src: s._show_ctx_menu(v, p, src)
        )
        vh = view.verticalHeader()
        if vh is not None:
            vh.setVisible(False)
        hh = view.horizontalHeader()
        if hh is not None:
            hh.setStretchLastSection(True)
        ly.addWidget(view)

        if is_src:
            self._src_db = db
            self._src_model = model
            self._src_view = view
            model.count_failed.connect(
                lambda msg: self._on_count_failed(msg, is_src=True)
            )
            db.currentIndexChanged.connect(
                lambda *_: self._apply_src_selection()
            )
        else:
            self._dst_db = db
            self._dst_model = model
            self._dst_view = view
            model.count_failed.connect(
                lambda msg: self._on_count_failed(msg, is_src=False)
            )
            db.currentIndexChanged.connect(
                lambda *_: self._apply_dst_selection()
            )

        # If both views exist and sync was enabled previously, apply now
        try:
            if (
                getattr(self, "_src_view", None) is not None
                and getattr(self, "_dst_view", None) is not None
            ):
                self._apply_sync_scroll_connections()
        except Exception as e:
            logger.log(VERBOSE, "TransferWidget: %s", e, exc_info=True)

        return w

    # -------------------------------
    # View state helpers (selection/scroll)
    # -------------------------------
    def _capture_view_state(self, view: QTableView, model: TablesModel):
        """Capture selected table names and vertical scroll value.

        Args:
            view: The table view.
            model: The underlying source model.

        Returns:
            A tuple (names, scroll_value) suitable for restoring later.
        """
        try:
            names = self._selected_tables(view, model)
        except Exception:
            names = []
        vsb = view.verticalScrollBar()
        scroll_val = vsb.value() if vsb is not None else 0
        return (names, scroll_val)

    def _restore_view_state(
        self, view: QTableView, model: TablesModel, state
    ) -> None:
        """Restore selection and vertical scroll after a model refresh.

        Args:
            view: The table view.
            model: The underlying source model.
            state: The state tuple returned by _capture_view_state.
        """
        if not state:
            return
        names, scroll_val = state
        proxy_model = view.model()
        # Select rows matching the saved names
        try:
            sel = view.selectionModel()
            if sel:
                sel.clearSelection()
            # Build a set for quick lookup
            wanted = set(names)
            # Iterate source model rows to find matches
            for r in range(model.rowCount()):
                name = model.table_name(r)
                if not name or name not in wanted:
                    continue
                src_idx = model.index(r, 0)
                try:
                    if isinstance(proxy_model, QSortFilterProxyModel):
                        px_idx = proxy_model.mapFromSource(src_idx)
                    else:
                        px_idx = src_idx
                except Exception:
                    px_idx = src_idx
                if not px_idx.isValid():
                    continue
                if sel:
                    flags = cast(
                        QItemSelectionModel.SelectionFlag,
                        (
                            QItemSelectionModel.SelectionFlag.Select
                            | QItemSelectionModel.SelectionFlag.Rows
                        ),
                    )
                    sel.select(px_idx, flags)
        except Exception as e:
            logger.log(VERBOSE, "TransferWidget: %s", e, exc_info=True)
        # Restore scroll position
        try:
            vsb = view.verticalScrollBar()
            if vsb is not None:
                vsb.setValue(scroll_val)
        except Exception as e:
            logger.log(VERBOSE, "TransferWidget: %s", e, exc_info=True)

    # Selection -> connections

    def _apply_src_selection(self) -> None:
        """Update source connection based on the chooser selection.

        Also enforces that destination is different; if same, clears dest.
        """
        logger.log(VERBOSE, "TransferWidget: applying src selection")
        self._src_count_error_shown = False

        # Capture view state to preserve selection/scroll across refreshes
        src_state = None
        dst_state = None
        try:
            src_state = self._capture_view_state(
                self._src_view, self._src_model
            )
        except Exception:
            src_state = None
        try:
            dst_state = self._capture_view_state(
                self._dst_view, self._dst_model
            )
        except Exception:
            dst_state = None

        cfg = self._current_cfg(self._src_db)
        if not cfg:
            self._src_conn = None
        else:
            self._src_conn = DbConn(
                c_string=cfg.get("c_string", ""),
                schema=cfg.get("schema", "public") or "public",
            )
        # Enforce different connections: if equal, clear destination
        if self._is_same_conn(self._src_conn, self._dst_conn):
            self._clear_destination()
        self._src_model.set_connections(self._src_conn, self._dst_conn)
        # Source selection changes table list; refresh both models
        self._src_model.refresh()
        try:
            self._dst_model.set_connections(self._src_conn, self._dst_conn)
            self._dst_model.refresh()
        except Exception as e:
            logger.log(VERBOSE, "TransferWidget: %s", e, exc_info=True)

        # Run counts in main thread for the new source (and dst if set)
        self._run_counts_sync("src")
        self._run_counts_sync("dst")

        # Restore view state asynchronously (after models settle)
        try:
            if src_state:
                QTimer.singleShot(
                    0,
                    lambda s=src_state: self._restore_view_state(
                        self._src_view, self._src_model, s
                    ),
                )
            if dst_state:
                QTimer.singleShot(
                    0,
                    lambda s=dst_state: self._restore_view_state(
                        self._dst_view, self._dst_model, s
                    ),
                )
        except Exception as e:
            logger.log(
                1,
                "TransferWidget: failed to schedule restore view state: %s",
                e,
                exc_info=True,
            )
        logger.log(
            VERBOSE,
            "TransferWidget: applied src selection %s",
            None if not cfg else cfg.get("id"),
        )

    def _apply_dst_selection(self) -> None:
        """Update destination connection based on the chooser selection.

        Enforces different source/destination by clearing destination if same.
        """
        logger.log(VERBOSE, "TransferWidget: applying dst selection")
        self._dst_count_error_shown = False

        cfg = self._current_cfg(self._dst_db)
        if not cfg:
            self._dst_conn = None
        else:
            self._dst_conn = DbConn(
                c_string=cfg.get("c_string", ""),
                schema=cfg.get("schema", "public") or "public",
            )
        # If same as source keep source and clear destination
        if self._is_same_conn(self._src_conn, self._dst_conn):
            self._clear_destination()
        # Update only destination-side model and refresh it
        # Destination selection does not affect table list; avoid full refreshes
        try:
            # Update both models' connections
            self._dst_model.set_connections(self._src_conn, self._dst_conn)
            self._src_model.set_connections(self._src_conn, self._dst_conn)
            # Invalidate only destination-side counts so deltas recollect
            self._dst_model.invalidate_counts_side("dst")
            self._src_model.invalidate_counts_side("dst")
            self._run_counts_sync("dst")
        except Exception as e:
            logger.error(
                (
                    "TransferWidget: failed to invalidate counts after "
                    "selection: %s"
                ),
                e,
                exc_info=True,
            )
        logger.log(
            VERBOSE,
            "TransferWidget: applied dst selection %s",
            None if not cfg else cfg.get("id"),
        )

    def _current_cfg(self, db: ChooseDb) -> Optional[dict]:
        """Extract the selected DB configuration dict from a ChooseDb.

        Args:
            db: The chooser to read from.

        Returns:
            The configuration dict or None if none selected.
        """
        idx = db.currentIndex()
        model = db.model()
        try:
            # DbConfigModel API
            from exdrf_qt.controls.seldb.db_config_model import DbConfigModel

            if isinstance(model, DbConfigModel):
                mi = model.index(idx, 0)
                return model.get_config(mi)
        except Exception as e:
            logger.log(VERBOSE, "TransferWidget: %s", e, exc_info=True)
        return None

    # Utilities enforcing different connections and selection of newest
    def _current_config_id(self, chooser: "ChooseDb") -> Optional[str]:
        """Return the currently selected configuration id for a chooser.

        Args:
            chooser: The database chooser.

        Returns:
            The selected configuration id or None.
        """
        try:
            from exdrf_qt.controls.seldb.db_config_model import DbConfigModel

            model = chooser.model()
            if not isinstance(model, DbConfigModel):
                return None
            idx = chooser.currentIndex()
            if idx < 0:
                return None
            cfg = model.get_config(model.index(idx, 0))
            if cfg:
                return cfg.get("id")
        except Exception as e:
            logger.log(VERBOSE, "TransferWidget: %s", e, exc_info=True)
        return None

    def _set_selection_by_id(
        self, chooser: "ChooseDb", cfg_id: Optional[str]
    ) -> bool:
        """Try to select a config by id in the provided chooser.

        Args:
            chooser: The database chooser to alter.
            cfg_id: The configuration id to select.

        Returns:
            True if the selection was changed to the id, False otherwise.
        """
        if not cfg_id:
            return False
        try:
            from exdrf_qt.controls.seldb.db_config_model import DbConfigModel

            model = chooser.model()
            if not isinstance(model, DbConfigModel):
                return False
            idx = model.find_config_index(cfg_id)
            if idx is not None:
                chooser.setCurrentIndex(idx.row())
                return True
        except Exception as e:
            logger.log(VERBOSE, "TransferWidget: %s", e, exc_info=True)
        return False

    def _is_same_conn(
        self, a: Optional["DbConn"], b: Optional["DbConn"]
    ) -> bool:
        """Compare two connections by connection string and schema.

        Args:
            a: First connection.
            b: Second connection.

        Returns:
            True if both are non-None and have identical c_string and schema.
        """
        if a is None or b is None:
            return False
        return a.c_string == b.c_string and a.schema == b.schema

    def _clear_destination(self) -> None:
        """Clear the destination selection and connection."""
        self._dst_conn = None
        try:
            self._dst_db.setCurrentIndex(-1)
        except Exception as e:
            logger.error(
                "TransferWidget: failed to clear destination: %s",
                e,
                exc_info=True,
            )

        self._src_model.set_connections(self._src_conn, self._dst_conn)
        self._dst_model.set_connections(self._src_conn, self._dst_conn)
        self._dst_model.refresh()

    def _select_newest_for_source(self) -> None:
        """Select the newest connection for the source chooser.

        Newest is determined by created_at if available, otherwise by
        the order in settings (last entry wins).
        """
        try:
            from exdrf_qt.controls.seldb.db_config_model import DbConfigModel

            model = self._src_db.model()
            if not isinstance(model, DbConfigModel):
                return

            configs = self.ctx.stg.get_db_configs()
            newest = None
            if configs:
                # Pick by max created_at if present, else last item
                def _key(c):
                    return c.get("created_at") or ""

                with_created = [c for c in configs if c.get("created_at")]
                if with_created:
                    newest = max(with_created, key=_key)
                else:
                    newest = configs[-1]
            if newest and newest.get("id"):
                idx = model.find_config_index(newest["id"])  # type: ignore
                if idx is not None:
                    self._src_db.setCurrentIndex(idx.row())
                    logger.log(
                        VERBOSE,
                        "TransferWidget: newest source id=%s",
                        newest["id"],
                    )
        except Exception as e:
            logger.error(
                "Failed to select newest for source: %s", e, exc_info=True
            )

    # Settings and bootstrap actions
    def _on_open_settings(self) -> None:
        """Open the database settings dialog and refresh the choosers after.

        Attempts to preserve current selections; if a selection disappears,
        falls back to newest on source and clears destination.
        """
        prev_src_id = None
        prev_dst_id = None
        try:
            from exdrf_qt.controls.seldb.sel_db import SelectDatabaseDlg

            # Preserve current selections
            prev_src_id = self._current_config_id(self._src_db)
            prev_dst_id = self._current_config_id(self._dst_db)

            dlg = SelectDatabaseDlg(
                ctx=self.ctx, parent=self, show_transfer_button=False
            )
            dlg.exec_()
        except Exception as e:
            logger.error("Failed to open settings dialog: %s", e, exc_info=True)
        finally:
            # Refresh both choosers to reflect any changes
            try:
                self._src_db.populate_db_connections()
                self._dst_db.populate_db_connections()

                # Try to restore previous selections
                restored_src = self._set_selection_by_id(
                    self._src_db, prev_src_id
                )
                restored_dst = self._set_selection_by_id(
                    self._dst_db, prev_dst_id
                )

                if not restored_src:
                    # Fallback to newest + empty
                    self._select_newest_for_source()
                if not restored_dst:
                    self._clear_destination()

                # Apply effects (update connections and models)
                self._apply_src_selection()
                self._apply_dst_selection()
                logger.log(
                    VERBOSE,
                    "TransferWidget: settings closed, restored src=%s dst=%s",
                    prev_src_id,
                    prev_dst_id,
                )
            except Exception as e:
                logger.error(
                    "Failed to restore selections: %s", e, exc_info=True
                )

    def _on_bootstrap_dst(self) -> None:
        """Run bootstrap on the selected destination connection."""
        cfg = self._current_cfg(self._dst_db)
        if not cfg:
            QMessageBox.information(
                self,
                self.t("cmn.info", "Info"),
                self.t("tr.no-dst", "No destination connection selected."),
            )
            return

        # Confirm with the user before proceeding
        conn_name = cfg.get("name") or cfg.get("c_string", "")
        question = self.t(
            "tr.bootstrap.confirm",
            "Bootstrap the destination database '{name}'?\nProceed?",
            name=conn_name,
        )
        reply = QMessageBox.question(
            self,
            self.t("cmn.question", "Question"),
            question,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # Build a temporary context to bootstrap this DB
        try:
            local_ctx = self.ctx.__class__(  # type: ignore
                c_string=cfg.get("c_string", ""),
                schema=cfg.get("schema", "public") or "public",
                top_widget=self.ctx.top_widget,
                work_relay=None,
                asset_sources=self.ctx.asset_sources,
                auto_migrate=False,
            )
            try:
                local_ctx.connect()
            except Exception as e:
                self.ctx.show_error(
                    title=self.ctx.t("cmn.error", "Error"),
                    message=self.ctx.t(
                        "cmn.db.err-connect",
                        "Failed to connect to the database using {cons}: {err}",
                        cons=local_ctx.c_string,
                        err=str(e),
                    ),
                )
                return
            try:
                if not local_ctx.bootstrap():
                    return
            except Exception as e:
                self.ctx.show_error(
                    title=self.ctx.t("cmn.error", "Error"),
                    message=self.ctx.t(
                        "cmn.db.err-bootstrap",
                        "Failed to bootstrap the database: {err}",
                        err=str(e),
                    ),
                )
                return
            QMessageBox.information(
                self,
                self.t("cmn.info", "Info"),
                self.t("cmn.db.bootstrap-success", "Bootstrap successful!"),
            )
        except Exception as e:
            logger.error("Bootstrap failed: %s", e, exc_info=True)

    # Context menu
    def _show_ctx_menu(
        self, view: QTableView, point: QPoint, is_src: bool
    ) -> None:
        """Show a context menu appropriate for the given table view.

        Args:
            view: The view that was right-clicked.
            point: Local position for the menu.
            is_src: Whether the menu is for the source pane.
        """
        menu = QMenu(view)
        act_view = QAction(self.t("tr.view", "View"), menu)
        act_view.triggered.connect(lambda: self._on_view_tables(view, is_src))
        menu.addAction(act_view)

        if is_src:
            act_transfer = QAction(self.t("tr.transfer.t", "Transfer"), menu)
            icon: Optional[QIcon]
            try:
                icon = self.get_icon("layer_aspect_arrow")
                act_transfer.setIcon(icon)
            except Exception:
                logger.error(
                    "Failed to get icon for transfer action", exc_info=True
                )
            act_transfer.triggered.connect(lambda: self._on_transfer(view))
            menu.addSeparator()
            menu.addAction(act_transfer)

        # Sync scroll toggle (check-mark reflects current state)
        act_sync = QAction(self.t("tr.sync.scroll", "Sync Scroll"), menu)
        act_sync.setCheckable(True)
        act_sync.setChecked(self._sync_scroll)
        act_sync.toggled.connect(self._set_sync_scroll)
        menu.addAction(act_sync)

        act_refresh = QAction(self.t("tr.refresh", "Refresh Counts"), menu)
        act_refresh.triggered.connect(lambda: self._on_refresh_counts(view))
        menu.addSeparator()
        menu.addAction(act_refresh)

        # Pluggy hook: let plugins add extra menu items (source or destination)
        hook = get_hook_safely(exdrf_qt_pm.hook, "transfer_context_menu")
        if hook is not None:
            menu.addSeparator()
            safe_hook_call(
                hook,
                transfer_widget=self,
                menu=menu,
                view=view,
                is_source_side=is_src,
            )

        vp = view.viewport()
        if vp is None:
            return

        menu.exec_(vp.mapToGlobal(point))

    def _on_refresh_counts(self, view: QTableView) -> None:
        """Refresh counts: clear both models and run sync count for both sides.

        Args:
            view: The view to refresh the counts for.
        """
        self._src_model.invalidate_counts()
        self._dst_model.invalidate_counts()
        self._run_counts_sync("src")
        self._run_counts_sync("dst")

    # Actions
    def _selected_tables(
        self, view: QTableView, model: TablesModel
    ) -> List[str]:
        """Return table names corresponding to the current selection.

        Args:
            view: The view to read the selection from.
            model: The backing list model.

        Returns:
            A list of selected table names.
        """
        sel = view.selectionModel()
        if not sel:
            return []
        indexes = sel.selectedRows(0)
        out: List[str] = []
        proxy_model = view.model()
        # Resolve the source model to access table_name()
        try:
            source_model = (
                proxy_model.sourceModel()  # type: ignore[attr-defined]
                if isinstance(proxy_model, QSortFilterProxyModel)
                else model
            )
        except Exception:
            source_model = model

        for idx in indexes:
            try:
                if isinstance(proxy_model, QSortFilterProxyModel):
                    src_idx = proxy_model.mapToSource(idx)
                    r = src_idx.row()
                else:
                    r = idx.row()
            except Exception:
                r = idx.row()
            # Lookup table name in the source model
            name = source_model.table_name(r)  # type: ignore[attr-defined]
            if name:
                out.append(name)
        return out

    def _on_view_tables(self, view: QTableView, is_src: bool) -> None:
        """Open the table viewer for selected tables on the proper connection.

        Args:
            view: The originating list view.
            is_src: True if viewing from the source pane.
        """
        model: TablesModel = view.model()  # type: ignore[assignment]
        tables = self._selected_tables(view, model)
        if not tables:
            return
        conn = self._src_conn if is_src else self._dst_conn
        if conn is None or conn.engine is None:
            try:
                engine = conn.connect() if conn else None
            except Exception:
                engine = None
        else:
            engine = conn.engine
        if engine is None:
            return

        win = self._src_view_win if is_src else self._dst_view_win
        if win is None:
            win = TableViewer(ctx=self.ctx)

            # Install plugin to transfer selected rows when viewing the source
            if is_src and self._dst_conn is not None:
                win.add_plugin(
                    TransferSelectedPlugin(
                        dst=self._dst_conn,
                        on_done=self._refresh_counts,
                        chunk=self._spin_chunk.value(),
                    )
                )

            win.destroyed.connect(
                lambda *_: self._on_viewer_closed(is_src=is_src)
            )
            title = (
                self.t("tr.src.viewer", "Source Tables")
                if is_src
                else self.t("tr.dst.viewer", "Destination Tables")
            )
            self.ctx.create_window(win, title)

            if is_src:
                self._src_view_win = win
            else:
                self._dst_view_win = win

        for t in tables:
            try:
                win.open_table(
                    engine=engine,
                    schema=conn.schema if conn else None,
                    table=t,
                )
            except Exception as e:
                logger.error("Failed to open table %s: %s", t, e, exc_info=True)

    def _on_viewer_closed(self, *, is_src: bool) -> None:
        """Clear viewer references when a viewer window is closed.

        Args:
            is_src: Which viewer was closed (source or destination).
        """
        if is_src:
            self._src_view_win = None
        else:
            self._dst_view_win = None

    def _on_transfer(self, view: QTableView) -> None:
        """Start a whole-table transfer for selected tables.

        Args:
            view: The source tables view.
        """
        tables = self._selected_tables(view, self._src_model)
        if not tables or not self._src_conn or not self._dst_conn:
            return
        worker = TransferWorker(
            src=self._src_conn,
            dst=self._dst_conn,
            tables=tables,
            chunk_size=self._spin_chunk.value(),
        )
        worker.error.connect(self._on_transfer_error)
        # Keep a reference so thread is not destroyed while running
        self._full_worker = worker
        logger.log(
            VERBOSE,
            "TransferWidget: start full transfer tables=%s chunk=%d",
            tables,
            self._spin_chunk.value(),
        )
        # Progress UI
        dlg = QProgressDialog(
            self.t("tr.transfer.t", "Transfer"),
            self.t("cmn.cancel", "Cancel"),
            0,
            0,
            self,
        )
        dlg.setWindowTitle(self.t("tr.transfer.t", "Transfer"))
        dlg.setAutoReset(True)
        dlg.setAutoClose(True)

        def _on_started(tbl: str, total: int) -> None:
            """Initialize the dialog range/label for the current table.

            Args:
                tbl: Current table name.
                total: Total rows to copy (0 if unknown).
            """
            if total > 0:
                dlg.setRange(0, total)
            else:
                dlg.setRange(0, 0)  # busy
            dlg.setValue(0)
            dlg.setLabelText(
                self.t(
                    "tr.transfer.table",
                    "Transferring {tbl}...",
                    tbl=tbl,
                )
            )

        def _on_progress(tbl: str, done: int, total: int) -> None:
            """Update dialog as rows are copied.

            Args:
                tbl: Current table name.
                done: Rows copied so far.
                total: Total rows in table (0 if unknown).
            """
            if total > 0:
                if dlg.maximum() != total:
                    dlg.setRange(0, total)
                dlg.setValue(done)
            dlg.setLabelText(
                self.t(
                    "tr.transfer.progress",
                    "Transferring {tbl}... {done}/{total}",
                    tbl=tbl,
                    done=done,
                    total=total,
                )
            )

        def _on_finished() -> None:
            """Refresh counts and close the dialog on completion."""
            dlg.setValue(dlg.maximum())
            dlg.close()
            self._refresh_counts()
            logger.log(VERBOSE, "TransferWidget: full transfer finished")

        def _on_canceled() -> None:
            """Cancel the running worker."""
            worker.requestInterruption()

        worker.table_started.connect(_on_started)
        worker.progress.connect(_on_progress)
        worker.finished_all.connect(_on_finished)
        worker.finished_all.connect(lambda: setattr(self, "_full_worker", None))
        dlg.canceled.connect(_on_canceled)
        worker.start()

    def _refresh_counts(self) -> None:
        """Rebuild table list and run sync counts for both sides."""
        self._src_model.refresh()
        self._dst_model.refresh()
        self._run_counts_sync("src")
        self._run_counts_sync("dst")

    def _run_counts_sync(self, side: str) -> None:
        """Run row counts in the main thread for one connection and update both
        models. Uses a single query to fetch all table counts at once.

        Args:
            side: "src" or "dst"; the connection that was changed or that we
                are (re)counting.
        """
        conn = self._src_conn if side == "src" else self._dst_conn
        if conn is None:
            return
        table_names = [
            self._src_model.table_name(row)
            for row in range(self._src_model.rowCount())
        ]
        table_names = [n for n in table_names if n]
        if not table_names:
            return
        counts = self._src_model.count_all_tables(conn, table_names)
        for row in range(self._src_model.rowCount()):
            name = self._src_model.table_name(row)
            if not name:
                continue
            val = counts.get(name, -1)
            self._src_model.set_count(row, side, val)
            self._dst_model.set_count(row, side, val)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Stop background threads before closing the widget."""
        try:
            if self._full_worker and self._full_worker.isRunning():
                self._full_worker.requestInterruption()
                self._full_worker.wait(2000)
        except Exception as e:
            logger.log(VERBOSE, "TransferWidget: %s", e, exc_info=True)
        # Disconnect sync scroll
        try:
            self._disconnect_sync_scroll()
        except Exception as e:
            logger.log(VERBOSE, "TransferWidget: %s", e, exc_info=True)
        super().closeEvent(event)

    # -------------------------------
    # Sync scroll helpers
    # -------------------------------
    def _toggle_sync_scroll(self) -> None:
        """Toggle sync scroll (legacy helper)."""
        self._set_sync_scroll(not self._sync_scroll)

    def _set_sync_scroll(self, enabled: bool) -> None:
        """Set sync scroll state and (dis)connect listeners accordingly.

        Args:
            enabled: Whether to enable synchronized scrolling.
        """
        self._sync_scroll = bool(enabled)
        self._apply_sync_scroll_connections()

    def _apply_sync_scroll_connections(self) -> None:
        """Connect or disconnect scrollbars based on current sync state."""
        self._disconnect_sync_scroll()
        if not self._sync_scroll:
            return
        if (
            getattr(self, "_src_view", None) is None
            or getattr(self, "_dst_view", None) is None
        ):
            return
        sv = self._src_view.verticalScrollBar()
        dv = self._dst_view.verticalScrollBar()
        try:
            sv.valueChanged.connect(self._on_src_scroll)
        except Exception as e:
            logger.log(VERBOSE, "TransferWidget: %s", e, exc_info=True)
        try:
            dv.valueChanged.connect(self._on_dst_scroll)
        except Exception as e:
            logger.log(VERBOSE, "TransferWidget: %s", e, exc_info=True)

    def _disconnect_sync_scroll(self) -> None:
        """Disconnect any existing sync scroll connections."""
        try:
            if getattr(self, "_src_view", None) is not None:
                sv = self._src_view.verticalScrollBar()
                sv.valueChanged.disconnect(self._on_src_scroll)
        except Exception as e:
            logger.log(VERBOSE, "TransferWidget: %s", e, exc_info=True)
        try:
            if getattr(self, "_dst_view", None) is not None:
                dv = self._dst_view.verticalScrollBar()
                dv.valueChanged.disconnect(self._on_dst_scroll)
        except Exception as e:
            logger.log(VERBOSE, "TransferWidget: %s", e, exc_info=True)

    def _on_src_scroll(self, value: int) -> None:
        """Propagate source scroll to destination when sync is enabled.

        Avoid recursive updates by using an in-progress guard and map the
        scroll value proportionally when maximums differ.
        """
        if (
            not self._sync_scroll
            or self._sync_in_progress
            or getattr(self, "_dst_view", None) is None
        ):
            return
        dv = self._dst_view.verticalScrollBar()
        sv = self._src_view.verticalScrollBar()
        try:
            self._sync_in_progress = True
            src_max = max(1, sv.maximum())
            dst_max = dv.maximum()
            mapped = int(
                round(min(max(0, value), src_max) * (dst_max / src_max))
            )
            dv.setValue(mapped)
        finally:
            self._sync_in_progress = False

    def _on_dst_scroll(self, value: int) -> None:
        """Propagate destination scroll to source when sync is enabled.

        Avoid recursive updates by using an in-progress guard and map the
        scroll value proportionally when maximums differ.
        """
        if (
            not self._sync_scroll
            or self._sync_in_progress
            or getattr(self, "_src_view", None) is None
        ):
            return
        sv = self._src_view.verticalScrollBar()
        dv = self._dst_view.verticalScrollBar()
        try:
            self._sync_in_progress = True
            dst_max = max(1, dv.maximum())
            src_max = sv.maximum()
            mapped = int(
                round(min(max(0, value), dst_max) * (src_max / dst_max))
            )
            sv.setValue(mapped)
        finally:
            self._sync_in_progress = False

    def _on_count_failed(self, message: str, is_src: bool) -> None:
        """Show count error toast once per connection selection.

        Args:
            message: Error message from the count worker.
            is_src: True for source side, False for destination.
        """
        if is_src and self._src_count_error_shown:
            return
        if not is_src and self._dst_count_error_shown:
            return
        from exdrf_qt.controls.toast import Toast

        Toast.show_error(self, message)
        if is_src:
            self._src_count_error_shown = True
        else:
            self._dst_count_error_shown = True

    def _on_transfer_error(self, table_name: str, message: str) -> None:
        """Handle transfer errors by showing the failure reason in a toast.

        Args:
            table_name: The table that failed to transfer.
            message: The exception or error message (reason for failure).
        """
        from exdrf_qt.controls.toast import Toast

        Toast.show_error(
            self,
            "%s: %s" % (table_name, message),
        )
