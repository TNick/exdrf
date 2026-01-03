"""UI widget for selecting and running checks with multiprocessing support."""

from __future__ import annotations

import inspect
import logging
import multiprocessing as mp
import sys
from collections import OrderedDict, defaultdict
from html import escape as html_escape
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from PyQt5.QtCore import (
    QEvent,
    QItemSelection,
    QItemSelectionModel,
    QModelIndex,
    QObject,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
    QButtonGroup,
    QFormLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QToolButton,
    QWidget,
)

try:
    from PyQt5.QtWinExtras import (
        QWinTaskbarButton,
        QWinTaskbarProgress,
    )
except Exception:  # pragma: no cover - optional on non-Windows
    QWinTaskbarButton = None  # type: ignore
    QWinTaskbarProgress = None  # type: ignore

from exdrf_util.task import TaskState

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.checks.available_delegate import AvailableChecksDelegate
from exdrf_qt.controls.checks.available_model import AvailableChecksModel
from exdrf_qt.controls.checks.check_manager_ui import Ui_ChecksManager
from exdrf_qt.controls.checks.checks_model_base import ChecksViewMode
from exdrf_qt.controls.checks.mp_executor import (
    WorkerMessage,
    run_check_task_in_process,
)
from exdrf_qt.controls.checks.results_model import ResultsModel, ResultsViewMode
from exdrf_qt.controls.checks.selected_delegate import SelectedChecksDelegate
from exdrf_qt.controls.checks.selected_model import SelectedChecksModel
from exdrf_qt.controls.param_controls import TaskParameterControlsMixin
from exdrf_qt.controls.seldb.choose_db import ChooseDb

if TYPE_CHECKING:
    from multiprocessing.context import SpawnContext, SpawnProcess
    from multiprocessing.queues import Queue
    from multiprocessing.synchronize import Event

    from exdrf_util.check import Check
    from exdrf_util.task import TaskParameter
    from PyQt5.QtWinExtras import QWinTaskbarButton, QWinTaskbarProgress

    from exdrf_qt.context import QtContext

logger = logging.getLogger(__name__)
POOL_INTERVAL = 500  # milliseconds


class CheckManager(
    QWidget, QtUseContext, Ui_ChecksManager, TaskParameterControlsMixin
):
    """A manager for selecting and running checks.

    Attributes:
        ctx: The Qt context.
        available_model: The model for available checks.
        selected_model: The model for selected checks.
        _filter_timer: Timer used to debounce filter changes in available view.
        _tab_group: Button group that controls the main stacked pages.
        _param_tab_buttons: Tab buttons for parameter categories.
        _param_pages: Pages inserted into ``c_stacked`` for parameter editing.
        _state: Current task state.
        results_model: Model that stores check results.
        _results_filter_timer: Timer used to debounce result filtering.
        mp_ctx: Multiprocessing context used to spawn worker processes.
            We use the spawn start method which launches a fresh Python
            interpreter, imports the main module, and then executes the
            target function. Child processes do not inherit the parent's
            memory state; everything must be picklable to cross the process
            boundary.
        mp_queue: Queue used to receive messages from worker processes.
        mp_stop: Event used to request worker termination.
        _mp_processes: Worker processes keyed by check id.
        mp_poll_timer: Timer polling the worker message queue.
        _pending_check_ids: Queue of check ids awaiting execution.
        _run_had_error: Whether any worker reported an error.
        _run_errors: Errors reported by workers keyed by check id.
        _taskbar_button: Taskbar button wrapper used for Windows progress.
        _taskbar_progress: Taskbar progress handle used for Windows progress.

    Signals:
        shouldClose: Emitted when the manager should close.
        shouldStart: Emitted when the manager should start.
        shouldRestart: Emitted when the manager should restart.
        progressChanged: Emitted when the total progress changes.
    """

    ctx: "QtContext"
    bootstrap_imports: List[str]

    available_model: AvailableChecksModel
    selected_model: SelectedChecksModel

    _filter_timer: QTimer
    _tab_group: QButtonGroup

    _param_tab_buttons: List[QPushButton]
    _param_pages: List[QWidget]

    _state: TaskState
    results_model: ResultsModel

    _results_filter_timer: QTimer

    mp_ctx: SpawnContext
    mp_queue: Optional["Queue[WorkerMessage]"]
    mp_stop: Optional[Event]
    _mp_processes: Dict[str, SpawnProcess]
    mp_poll_timer: QTimer
    _pending_check_ids: List[str]
    _run_had_error: bool
    _run_errors: Dict[str, str]
    _taskbar_button: Optional[Any]
    _taskbar_progress: Optional[Any]

    shouldClose = pyqtSignal()
    shouldStart = pyqtSignal()
    shouldRestart = pyqtSignal()
    progressChanged = pyqtSignal(int)

    def __init__(
        self,
        ctx: "QtContext",
        bootstrap_imports: List[str],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.ctx = ctx
        self.setup_ui(self)
        self.bootstrap_imports = bootstrap_imports

        # Configure models and views.
        self.available_model = AvailableChecksModel(ctx=ctx, parent=self)
        self.selected_model = SelectedChecksModel(ctx=ctx, parent=self)
        self.results_model = ResultsModel(ctx=ctx, parent=self)
        self._param_tab_buttons = []
        self._param_pages = []

        # Configure multiprocessing.
        self.mp_ctx = mp.get_context("spawn")
        self.mp_queue = None
        self.mp_stop = None
        self._mp_processes = {}
        self._pending_check_ids = []
        self._run_had_error = False
        self._run_errors = {}
        self._taskbar_button = None
        self._taskbar_progress = None

        self.mp_poll_timer = QTimer(self)
        self.mp_poll_timer.setInterval(POOL_INTERVAL)
        self.mp_poll_timer.timeout.connect(self.on_poll_worker_messages)

        # Configure UI wiring.
        self._setup_views()
        self._setup_context_menus()
        self._setup_filter_debouncer()
        self._setup_results()
        self._setup_tab_group()

        # Initial sync (selected exclusions, parameter pages, view mode).
        self._sync_models()
        self._rebuild_parameter_pages()

        # Configure state machine.
        self._state = TaskState.INPUT
        self.progressChanged.connect(self._on_total_progress_changed)
        self._react_to_state(self._state)

    def _setup_views(self) -> None:
        """Configure the two views and connect basic signals."""
        available_delegate = AvailableChecksDelegate(self)
        selected_delegate = SelectedChecksDelegate(self)

        # Configure the available view.
        self._configure_tree_view(self.c_available)
        self.c_available.setModel(self.available_model)
        self.c_available.setItemDelegate(available_delegate)
        self.c_available.doubleClicked.connect(
            self._on_available_double_clicked
        )

        # Configure the selected view.
        self._configure_tree_view(self.c_selected)
        self.c_selected.setModel(self.selected_model)
        self.c_selected.setItemDelegate(selected_delegate)
        self.c_selected.doubleClicked.connect(self._on_selected_double_clicked)

        # Ensure row heights are recalculated when the view width changes.
        self._install_relayout_on_resize(self.c_available)
        self._install_relayout_on_resize(self.c_selected)
        self._install_relayout_on_resize(self.c_results)

        # Configure selected view column behavior.
        self._apply_selected_column_layout(False)
        self._init_taskbar_progress()

        # Wire add/remove buttons.
        self.c_add.clicked.connect(self._on_add_clicked)
        self.c_remove.clicked.connect(self._on_remove_clicked)

        # Wire bottom buttons.
        self.c_main_button.clicked.connect(self._on_main_clicked)
        self.c_cancel_button.clicked.connect(self._on_cancel_clicked)

        # Ensure both models start in category mode.
        self.available_model.set_view_mode(ChecksViewMode.CATEGORY)
        self.selected_model.set_view_mode(ChecksViewMode.CATEGORY)
        self._apply_view_mode_to_view(self.c_available, ChecksViewMode.CATEGORY)
        self._apply_view_mode_to_view(self.c_selected, ChecksViewMode.CATEGORY)

        # Hide progress by default.
        self.c_progress.hide()

    def _setup_context_menus(self) -> None:
        """Enable and wire right-click menus on the two views."""
        self.c_available.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.c_available.customContextMenuRequested.connect(
            self._on_available_context_menu
        )

        self.c_selected.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.c_selected.customContextMenuRequested.connect(
            self._on_selected_context_menu
        )

    def _setup_filter_debouncer(self) -> None:
        """Debounce the available filter line edit and apply to the model."""
        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(300)
        self._filter_timer.timeout.connect(self._apply_available_filter)

        self.c_available_filter.textChanged.connect(
            self._on_filter_text_changed
        )

    def _setup_results(self) -> None:
        """Configure the results page widgets."""
        self._configure_tree_view(self.c_results)
        self.c_results.setModel(self.results_model)
        self.c_results.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        sel_model = self.c_results.selectionModel()
        if sel_model is not None:
            sel_model.selectionChanged.connect(
                self._on_results_selection_changed
            )

        self.c_results.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.c_results.customContextMenuRequested.connect(
            self._on_results_context_menu
        )

        self._results_filter_timer = QTimer(self)
        self._results_filter_timer.setSingleShot(True)
        self._results_filter_timer.setInterval(300)
        self._results_filter_timer.timeout.connect(self._apply_results_filter)

        self.c_results_filter.textChanged.connect(
            lambda _t: self._results_filter_timer.start()
        )

        # Configure the results type filter button (menu shown on click).
        self.c_type_filter.setIcon(self.get_icon("filter"))
        self.c_type_filter.setPopupMode(QToolButton.InstantPopup)
        self._results_type_menu = QMenu(self)
        self._results_type_menu.aboutToShow.connect(
            self._rebuild_results_type_menu
        )
        self.c_type_filter.setMenu(self._results_type_menu)

        # Keep grouped results expanded by default (initially and after each
        # model reset from new results / filtering / sorting).
        self.results_model.modelReset.connect(self._expand_results_if_grouped)
        self._expand_results_if_grouped()

        self.c_result_details.setOpenExternalLinks(False)
        self.c_result_details.setHtml("")

    def _setup_tab_group(self) -> None:
        """Set up the button group that controls ``c_stacked`` navigation."""
        self._tab_group = QButtonGroup(self)
        self._tab_group.setExclusive(True)
        self._tab_group.addButton(self.c_checks_tab, 0)
        self._tab_group.addButton(self.c_results_tab, 1)
        self._tab_group.idClicked.connect(self.c_stacked.setCurrentIndex)
        self.c_stacked.setCurrentIndex(0)

    def _configure_tree_view(self, view) -> None:
        """Apply common configuration for variable-height item rendering.

        Args:
            view: Target tree-like view to configure.
        """
        view.setHeaderHidden(True)
        view.setUniformRowHeights(False)
        view.setWordWrap(True)
        view.setTextElideMode(Qt.TextElideMode.ElideNone)
        view.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        view.setSortingEnabled(False)

    def _install_relayout_on_resize(self, view) -> None:
        """Install a resize handler that recomputes row heights.

        Args:
            view: A QTreeView-like widget.
        """
        viewport = view.viewport()
        if viewport is None:
            return
        viewport.installEventFilter(self)

    def eventFilter(
        self, a0: Optional[QObject], a1: Optional[QEvent]
    ) -> bool:  # noqa: N802
        """React to viewport resize events to recompute row heights.

        Args:
            a0: Event source widget.
            a1: Event being processed.

        Returns:
            True if the event is handled, False otherwise.
        """
        if a0 is None or a1 is None:
            return super().eventFilter(a0, a1)

        if a1.type() == QEvent.Type.Resize:
            if a0 is self.c_available.viewport():
                self.c_available.doItemsLayout()
            elif a0 is self.c_selected.viewport():
                self.c_selected.doItemsLayout()
            elif a0 is self.c_results.viewport():
                self.c_results.doItemsLayout()

        return super().eventFilter(a0, a1)

    def _apply_view_mode_to_view(self, view, mode: ChecksViewMode) -> None:
        """Configure view visuals for the given mode.

        Args:
            view: View to update.
            mode: View mode to apply.
        """
        if mode == ChecksViewMode.FLAT:
            view.setRootIsDecorated(False)
            view.setItemsExpandable(False)
            view.setExpandsOnDoubleClick(False)
            view.collapseAll()
        else:
            view.setRootIsDecorated(True)
            view.setItemsExpandable(True)
            view.setExpandsOnDoubleClick(False)
            view.expandAll()

    def _expand_results_if_grouped(self) -> None:
        """Expand results view if the model is in grouped mode."""
        if self.results_model.get_view_mode() != ResultsViewMode.GROUPED:
            return

        self.c_results.expandAll()

    def _apply_results_filter(self) -> None:
        """Apply the current filter to the results model."""
        self.results_model.set_filter_text(self.c_results_filter.text())

    def _on_results_context_menu(self, pos) -> None:
        """Show context menu for results view.

        Args:
            pos: Position where the menu is requested.
        """
        menu = QMenu(self)

        act_grouped = QAction(
            self.t("results.view.grouped", "Grouped view"),
            self,
        )
        act_grouped.setCheckable(True)
        act_flat = QAction(self.t("results.view.flat", "Flat view"), self)
        act_flat.setCheckable(True)

        mode = self.results_model.get_view_mode()
        act_grouped.setChecked(mode == ResultsViewMode.GROUPED)
        act_flat.setChecked(mode == ResultsViewMode.FLAT)

        act_grouped.triggered.connect(
            lambda: self.results_model.set_view_mode(ResultsViewMode.GROUPED)
        )
        act_flat.triggered.connect(
            lambda: self.results_model.set_view_mode(ResultsViewMode.FLAT)
        )
        menu.addAction(act_grouped)
        menu.addAction(act_flat)
        menu.addSeparator()

        # Expand/collapse actions (only enabled in grouped view).
        act_expand_all = QAction(
            self.t("results.expand_all", "Expand all"),
            self,
        )
        act_collapse_all = QAction(
            self.t("results.collapse_all", "Collapse all"),
            self,
        )
        act_expand_all.triggered.connect(self.c_results.expandAll)
        act_collapse_all.triggered.connect(self.c_results.collapseAll)
        act_expand_all.setEnabled(mode == ResultsViewMode.GROUPED)
        act_collapse_all.setEnabled(mode == ResultsViewMode.GROUPED)
        menu.addAction(act_expand_all)
        menu.addAction(act_collapse_all)
        menu.addSeparator()

        act_sort_asc = QAction(
            self.t("results.sort.asc", "Sort ascending"),
            self,
        )
        act_sort_desc = QAction(
            self.t("results.sort.desc", "Sort descending"),
            self,
        )
        act_sort_asc.triggered.connect(
            lambda: self.results_model.sort(0, Qt.SortOrder.AscendingOrder)
        )
        act_sort_desc.triggered.connect(
            lambda: self.results_model.sort(0, Qt.SortOrder.DescendingOrder)
        )
        menu.addAction(act_sort_asc)
        menu.addAction(act_sort_desc)

        # Result type (state) filtering.
        menu.addSeparator()
        types_menu = menu.addMenu(self.t("results.types.t", "Types"))
        self._populate_results_type_menu(types_menu)

        menu.exec_(self.c_results.viewport().mapToGlobal(pos))

    def _rebuild_results_type_menu(self) -> None:
        """Rebuild the toolbutton menu for filtering result types."""
        self._populate_results_type_menu(self._results_type_menu, clear=True)

    def _populate_results_type_menu(
        self, menu: QMenu, clear: bool = False
    ) -> None:
        """Populate a menu with checkable result type filters.

        Args:
            menu: Menu instance to populate.
            clear: Whether to clear the menu before populating.
        """
        if clear:
            menu.clear()

        present = self.results_model.get_present_states()
        if not present:
            act_empty = QAction(
                self.t("results.types.none", "(no results)"), self
            )
            act_empty.setEnabled(False)
            menu.addAction(act_empty)
            return

        hidden = self.results_model.get_hidden_states()
        ordered = [
            "failed",
            "passed",
            "skipped",
            "fixed",
            "partially_fixed",
            "not_fixed",
        ]
        rest = sorted([s for s in present if s not in ordered], key=str.lower)
        states = [s for s in ordered if s in present] + rest

        # Convenience actions.
        act_show_all = QAction(
            self.t("results.types.show_all", "Show all"), self
        )
        act_hide_all = QAction(
            self.t("results.types.hide_all", "Hide all"), self
        )
        act_show_all.triggered.connect(
            lambda: self.results_model.set_hidden_states(set())
        )
        act_hide_all.triggered.connect(
            lambda: self.results_model.set_hidden_states(set(states))
        )
        menu.addAction(act_show_all)
        menu.addAction(act_hide_all)
        menu.addSeparator()

        def label_for_state(state: str) -> str:
            return {
                "failed": self.t("results.types.failed", "Failed"),
                "passed": self.t("results.types.passed", "Passed"),
                "skipped": self.t("results.types.skipped", "Skipped"),
                "fixed": self.t("results.types.fixed", "Fixed"),
                "partially_fixed": self.t(
                    "results.types.partially_fixed", "Partially fixed"
                ),
                "not_fixed": self.t("results.types.not_fixed", "Not fixed"),
            }.get(state, state)

        for state in states:
            act = QAction(label_for_state(state), self)
            act.setCheckable(True)
            act.setChecked(state not in hidden)

            def on_toggle(checked: bool, s: str = state) -> None:
                new_hidden = self.results_model.get_hidden_states()
                if checked:
                    new_hidden.discard(s)
                else:
                    new_hidden.add(s)
                self.results_model.set_hidden_states(new_hidden)

            act.toggled.connect(on_toggle)
            menu.addAction(act)

    def _on_results_selection_changed(self, *_args: Any) -> None:
        """Populate the details browser for the selected result.

        Args:
            *_args: Unused selection change arguments.
        """
        sel = self.c_results.selectionModel()
        if sel is None:
            self.c_result_details.setHtml("")
            return

        rows = sel.selectedRows(0)
        if len(rows) != 1:
            self.c_result_details.setHtml("")
            return

        entry = self.results_model.get_entry_for_index(rows[0])
        if entry is None:
            self.c_result_details.setHtml("")
            return

        # Build HTML details.
        t_key = str(entry.result.get("t_key", "") or "")
        res_text = ""
        if t_key:
            res_text = self.t(
                str(entry.result.get("t_key", "") or ""),
                "",
                **dict(entry.result.get("params", {}) or {}),
            )
        if not res_text:
            res_text = entry.result.get("description", None)
            if not res_text:
                res_text = self.t("checks.result.unknown", "No description")

        params_lines = []
        for k, v in entry.params_values.items():
            params_lines.append(
                f"<b>{html_escape(k)}</b>: {html_escape(str(v))}"
            )
        params_html = "<br/>".join(params_lines)

        r_param_lines = []
        for k, v in entry.result.get("params", {}).items():
            r_param_lines.append(
                f"<b>{html_escape(k)}</b>: {html_escape(str(v))}"
            )
        r_params_html = "<br/>".join(r_param_lines)

        html_text = (
            f"<h3>{html_escape(entry.check_category)}</h3>"
            f"<h4>{html_escape(entry.check_title)}</h4>"
            f"<p>{html_escape(entry.check_description)}</p>"
            f"<h4>Parameters</h4>"
            f"<p>{params_html}</p>"
            f"<h4>Description</h4>"
            f"<p>{html_escape(res_text)}</p>"
            f"<h4>Result parameters</h4>"
            f"<p>{r_params_html}</p>"
        )
        self.c_result_details.setHtml(html_text)

    # ------------------------------------------------------------------
    # State machine (run/reset)
    # ------------------------------------------------------------------

    def _set_state(self, state: TaskState) -> None:
        """Update internal state and refresh UI bindings.

        Args:
            state: Desired task state to apply.
        """
        if state == self._state:
            return
        self._state = state
        self._react_to_state(state)

    def _react_to_state(self, state: TaskState) -> None:
        """Apply UI changes for the current task state.

        Args:
            state: Current task state driving the UI.
        """
        if state == TaskState.INPUT:
            self.c_progress.hide()
            self.c_progress.setRange(0, 100)
            self.c_progress.setValue(0)
            self._set_taskbar_progress(None, False)

            self.c_main_button.setEnabled(True)
            self.c_main_button.setText(self.t("checks.run", "Run"))

            self.c_cancel_button.setEnabled(True)
            self.c_cancel_button.setText(self.t("checks.cancel", "Cancel"))

            self._set_inputs_enabled_for_state(TaskState.INPUT)

            exp_state = self._snapshot_category_state(self.c_selected)
            self.selected_model.set_running(False)
            self._restore_category_state(self.c_selected, *exp_state)
            self._apply_selected_column_layout(False)
        elif state == TaskState.RUNNING:
            self.c_main_button.setEnabled(False)
            self.c_main_button.setText(self.t("checks.running", "Running..."))

            self.c_cancel_button.setEnabled(True)
            self.c_cancel_button.setText(self.t("checks.cancel", "Cancel"))

            # Keep expand/collapse functional while running.
            self._set_inputs_enabled_for_state(TaskState.RUNNING)

            exp_state = self._snapshot_category_state(self.c_selected)
            self.selected_model.set_running(True)
            self._restore_category_state(self.c_selected, *exp_state)
            self._apply_selected_column_layout(True)
            self._set_taskbar_progress(0, False)
        elif state in (TaskState.COMPLETED, TaskState.FAILED):
            self.c_progress.hide()
            self.c_progress.setRange(0, 100)
            self._set_taskbar_progress(None, False)

            self.c_main_button.setEnabled(True)
            self.c_main_button.setText(self.t("checks.reset", "Reset"))

            self.c_cancel_button.setEnabled(True)
            self.c_cancel_button.setText(self.t("checks.cancel", "Cancel"))

            self._set_inputs_enabled_for_state(state)

            exp_state = self._snapshot_category_state(self.c_selected)
            self.selected_model.set_running(False)
            self._restore_category_state(self.c_selected, *exp_state)
            self._apply_selected_column_layout(False)
        else:
            raise ValueError(f"Invalid state: {state}")

    def _apply_selected_column_layout(self, running: bool) -> None:
        """Set column sizing for the selected checks view.

        Args:
            running: Whether checks are running (progress column visible).
        """

        header = self.c_selected.header()
        if header is None:
            return

        # Keep header hidden while still controlling section sizing.
        header.setHidden(True)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        if running and self.selected_model.columnCount() > 1:
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            self.c_selected.setColumnWidth(1, 90)
            header.setMinimumSectionSize(40)
        else:
            # Ensure leftover space goes to the title when only one column.
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

    def _init_taskbar_progress(self) -> None:
        """Initialize Windows taskbar progress (standalone only)."""

        if self._taskbar_progress is not None:
            return

        if not getattr(self.ctx, "is_standalone", False):
            return

        if not sys.platform.startswith("win"):
            return

        taskbar_button_cls = QWinTaskbarButton
        progress_cls = QWinTaskbarProgress
        if taskbar_button_cls is None or progress_cls is None:
            return
        assert taskbar_button_cls is not None
        assert progress_cls is not None

        win = self.window()
        handle = win.windowHandle() if win is not None else None
        if handle is None:
            return

        taskbar_button = taskbar_button_cls(self)
        taskbar_button.setWindow(handle)
        tb_progress = taskbar_button.progress()
        self._taskbar_button = taskbar_button
        self._taskbar_progress = tb_progress
        if tb_progress is not None:
            tb_progress.setVisible(False)

    def _set_taskbar_progress(
        self, progress: Optional[int], indeterminate: bool
    ) -> None:
        """Update Windows taskbar progress indicator."""

        if not getattr(self.ctx, "is_standalone", False):
            return

        if not sys.platform.startswith("win"):
            return

        tb_progress = self._taskbar_progress
        if tb_progress is None:
            self._init_taskbar_progress()

        tb_progress = self._taskbar_progress
        if tb_progress is None:
            return

        if progress is None and not indeterminate:
            tb_progress.hide()
            return

        tb_progress.show()

        if indeterminate:
            tb_progress.setRange(0, 0)
            return

        if progress is None:
            tb_progress.hide()
            return

        progress_int = int(progress)
        safe_value = max(0, min(100, progress_int))
        tb_progress.setRange(0, 100)
        tb_progress.setValue(safe_value)

    def _set_inputs_enabled_for_state(self, state: TaskState) -> None:
        """Enable/disable inputs based on running state.

        While running we still allow expanding/collapsing the selected list.

        Args:
            state: Current task state.
        """
        if state == TaskState.RUNNING:
            self.c_available.setEnabled(False)
            self.c_available_filter.setEnabled(False)
            self.c_add.setEnabled(False)
            self.c_remove.setEnabled(False)

            # Allow expand/collapse while running.
            self.c_selected.setEnabled(True)

            # Disable parameter controls while running.
            for page in self._param_pages:
                page.setEnabled(False)
            if (
                hasattr(self, "_db_connection")
                and self._db_connection is not None
            ):
                self._db_connection.setEnabled(False)
            return

        enabled = state == TaskState.INPUT
        self.c_available.setEnabled(enabled)
        self.c_available_filter.setEnabled(enabled)
        self.c_add.setEnabled(enabled)
        self.c_remove.setEnabled(enabled)
        self.c_selected.setEnabled(enabled)
        for page in self._param_pages:
            page.setEnabled(enabled)
        if hasattr(self, "_db_connection") and self._db_connection is not None:
            self._db_connection.setEnabled(enabled)

    def _on_cancel_clicked(self) -> None:
        """Handle cancel button clicks."""
        if self._state in (
            TaskState.INPUT,
            TaskState.COMPLETED,
            TaskState.FAILED,
        ):
            self.shouldClose.emit()
            return

        self._cancel_running_checks()

    def _on_main_clicked(self) -> None:
        """Handle main button clicks based on current state."""
        if self._state == TaskState.INPUT:
            self.shouldStart.emit()
            self._start_checks()
            return

        if self._state in (TaskState.COMPLETED, TaskState.FAILED):
            self.shouldRestart.emit()
            self._reset()
            return

        raise ValueError(f"Invalid state: {self._state}")

    def _reset(self) -> None:
        """Reset results and selection."""
        self._cancel_running_checks()
        self.results_model.clear()
        self.c_results_filter.setText("")
        self.c_result_details.setHtml("")

        removed = self.selected_model.remove_checks_by_id(
            set(self.selected_model.get_check_ids())
        )
        self.available_model.put_back_checks(removed)
        self._sync_models()
        self._rebuild_parameter_pages()

        self.c_checks_tab.setChecked(True)
        self.c_stacked.setCurrentIndex(0)
        self._set_state(TaskState.INPUT)

    def _get_db_config(self) -> Dict[str, Any]:
        """Get DB config from the first parameter page control if present."""
        cfg: Dict[str, Any] = {}
        widget = getattr(self, "_db_connection", None)
        if isinstance(widget, ChooseDb):
            model: Any = widget.model()
            idx = widget.currentIndex()
            if model is not None and hasattr(model, "get_config"):
                q_idx = model.index(idx, 0)  # type: ignore[call-arg]
                conf = model.get_config(q_idx)
                if conf:
                    cfg = dict(conf)
        return cfg

    def _start_checks(self) -> None:
        """Start all selected checks using worker processes."""
        checks = self.selected_model.get_checks()
        if not checks:
            QMessageBox.information(
                self,
                self.t("checks.none.title", "No checks"),
                self.t("checks.none.msg", "Please select at least one check."),
            )
            return

        self.results_model.clear()
        self.c_result_details.setHtml("")

        self._pending_check_ids = [chk.check_id for chk in checks]
        self._run_had_error = False
        self._run_errors = {}
        self._set_state(TaskState.RUNNING)

        # Prepare progress bookkeeping.
        for cid in self._pending_check_ids:
            self.selected_model.set_check_progress(cid, -1, indeterminate=False)

        self.mp_queue = self.mp_ctx.Queue()
        self.mp_stop = self.mp_ctx.Event()

        self._start_process_pool()
        self.mp_poll_timer.start()

    def _get_max_workers(self) -> int:
        """Get max parallel workers from settings."""
        value = self.ctx.stg.get_setting("exdrf.checks.max_workers", 64)
        try:
            value_int = int(value)
        except Exception:
            value_int = 4
        return max(1, min(value_int, 64))

    def _start_process_pool(self) -> None:
        """Start as many worker processes as allowed."""
        if self.mp_queue is None or self.mp_stop is None:
            return

        max_workers = self._get_max_workers()
        db_cfg = self._get_db_config()

        while self._pending_check_ids and len(self._mp_processes) < max_workers:
            check_id = self._pending_check_ids.pop(0)

            # Snapshot parameter values for this check (inputs are disabled).
            values: Dict[str, Any] = {}
            chk: Optional["Check"] = None
            for chk in self.selected_model.get_checks():
                if chk.check_id != check_id:
                    continue
                for p in chk.parameters.values():
                    values[p.name] = p.value
            assert chk is not None
            mod = inspect.getmodule(chk)
            bootstrap_imports = [*self.bootstrap_imports]
            if mod and mod.__name__ not in ("__main__",):
                bootstrap_imports.append(mod.__name__)

            proc = self.mp_ctx.Process(
                target=run_check_task_in_process,
                kwargs={
                    "check_id": check_id,
                    "db": db_cfg,
                    "param_values": values,
                    "out_q": self.mp_queue,
                    "stop_event": self.mp_stop,
                    "bootstrap_imports": bootstrap_imports,
                },
            )
            proc.daemon = True
            proc.start()
            self._mp_processes[check_id] = proc

    def _cancel_running_checks(self) -> None:
        """Stop all running worker processes and clean up resources."""
        if self.mp_stop is not None:
            self.mp_stop.set()

        for proc in list(self._mp_processes.values()):
            try:
                if proc.is_alive():
                    proc.terminate()
                proc.join(timeout=0.5)
            except Exception:
                pass

        self.mp_poll_timer.stop()
        self._mp_processes = {}
        self.mp_queue = None
        self.mp_stop = None
        if self._state == TaskState.RUNNING:
            self._finish_run(success=False)

    def on_poll_worker_messages(self) -> None:
        """Poll worker messages from the queue."""
        q: Optional["Queue[WorkerMessage]"] = self.mp_queue
        if q is None:
            return

        # Drain queue.
        drained = 0
        while drained < 100:
            try:
                msg = q.get_nowait()
            except Exception:
                break
            drained += 1
            self._handle_worker_message(msg)

        # Reap finished processes.
        finished: List[str] = []
        for check_id, proc in list(self._mp_processes.items()):
            if not proc.is_alive():
                try:
                    proc.join(timeout=0.1)
                except Exception:
                    pass
                finished.append(check_id)

        for check_id in finished:
            self._mp_processes.pop(check_id, None)

        # Start new workers if needed.
        self._start_process_pool()

        # If all done, finish run.
        if not self._pending_check_ids and not self._mp_processes:
            self.mp_poll_timer.stop()
            self.mp_queue = None
            self.mp_stop = None
            self._finish_run(success=not self._run_had_error)

    def _handle_worker_message(self, msg: "WorkerMessage") -> None:
        """Route worker message to the appropriate handler.

        Args:
            msg: Message emitted by a worker process.
        """
        msg_type = msg.get("type")
        check_id = str(msg.get("check_id", "") or "")
        if msg_type == "progress":
            progress = int(msg.get("progress", -1))
            max_steps = int(msg.get("max_steps", -1))
            indeterminate = progress < 0 or max_steps <= 0
            self.selected_model.set_check_progress(
                check_id,
                progress,
                indeterminate=indeterminate,
            )
            self._update_total_progress()
            return

        if msg_type == "results":
            res_list = msg.get("results", [])
            check_title = str(msg.get("check_title", "") or "")
            check_desc = str(msg.get("check_description", "") or "")
            check_cat = str(msg.get("check_category", "") or "")

            # Capture parameter values as shown in UI for this check.
            values: Dict[str, Any] = {}
            for chk in self.selected_model.get_checks():
                if chk.check_id != check_id:
                    continue
                for p in chk.parameters.values():
                    values[p.name] = p.value

            results = []
            for r in res_list:
                results.append(dict(r))

            # If no results, add a synthetic "passed" entry indicating this.
            if not results:
                results.append(
                    {
                        "state": "passed",
                        "t_key": "checks.no_results",
                        "description": "No records were identified by this check",
                        "params": {},
                    }
                )

            self.results_model.add_results(
                check_id=check_id,
                check_title=check_title,
                check_description=check_desc,
                check_category=check_cat,
                params_values=values,
                results=results,
            )
            return

        if msg_type == "error":
            err = str(msg.get("error", "") or "")
            logger.error("Check %s failed: %s", check_id, err)
            self._run_had_error = True
            if check_id:
                self._run_errors[check_id] = err
                self.selected_model.set_check_failed(check_id)
            return

    def _update_total_progress(self) -> None:
        """Update c_progress based on per-check progress."""
        progress_by_id, indeterminate = (
            self.selected_model.get_progress_snapshot()
        )

        # If at least one task is indeterminate, show continuous progress.
        if indeterminate:
            self.c_progress.show()
            self.c_progress.setRange(0, 0)
            self._set_taskbar_progress(None, True)
            return

        if not progress_by_id:
            self._set_taskbar_progress(None, False)
            return

        total = 0
        for val in progress_by_id.values():
            if val is None or val < 0:
                continue
            total += min(100, int(val))

        avg = int(total / max(1, len(progress_by_id)))
        self.progressChanged.emit(avg)
        self._set_taskbar_progress(avg, False)

    def _on_total_progress_changed(self, progress: int) -> None:
        """Update the visible progress bar when total progress changes.

        Args:
            progress: Aggregated progress percentage.
        """
        self.c_progress.show()
        if self.c_progress.maximum() != 100 or self.c_progress.minimum() != 0:
            self.c_progress.setRange(0, 100)
        self.c_progress.setValue(progress)

    def _finish_run(self, success: bool) -> None:
        """Finalize run and switch to results page."""
        self.mp_poll_timer.stop()
        self._mp_processes = {}
        self.mp_queue = None
        self.mp_stop = None

        self._set_state(TaskState.COMPLETED if success else TaskState.FAILED)

        # Switch to results page.
        self.c_results_tab.setChecked(True)
        # Results tab is always the last page id in our tab group.
        self.c_stacked.setCurrentIndex(self.c_stacked.count() - 1)

        # Surface worker failures to the user (not only logs).
        if self._run_errors:
            title_map = {
                chk.check_id: chk.title
                for chk in self.selected_model.get_checks()
            }
            lines = []
            for cid, err in self._run_errors.items():
                name = title_map.get(cid, cid)
                lines.append(f"{name}: {err}")

            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Critical)
            box.setWindowTitle(
                self.t("checks.run.failed.title", "Checks failed")
            )
            box.setText(
                self.t(
                    "checks.run.failed.msg",
                    "One or more checks failed. See details for errors.",
                )
            )
            box.setDetailedText("\n".join(lines))
            box.exec_()

    def _on_filter_text_changed(self, text: str) -> None:
        """Handle filter typing with a debounce timer.

        Args:
            text: Current filter text.
        """
        del text
        self._filter_timer.stop()
        self._filter_timer.start()

    def _apply_available_filter(self) -> None:
        """Apply the current filter string to the available model."""
        self.available_model.set_filter_text(self.c_available_filter.text())
        self.c_available.expandAll()

    def _on_available_context_menu(self, pos) -> None:
        """Show context menu for the available checks view.

        Args:
            pos: Position where the menu is requested.
        """
        menu = QMenu(self)

        # Refresh.
        act_refresh = QAction(self.t("checks.refresh", "Refresh"), self)
        act_refresh.triggered.connect(self._on_refresh_available)
        menu.addAction(act_refresh)
        menu.addSeparator()

        # View mode.
        act_category = QAction(
            self.t("checks.view.category", "Category view"),
            self,
        )
        act_category.setCheckable(True)
        act_flat = QAction(self.t("checks.view.flat", "Flat view"), self)
        act_flat.setCheckable(True)

        mode = self.available_model.get_view_mode()
        act_category.setChecked(mode == ChecksViewMode.CATEGORY)
        act_flat.setChecked(mode == ChecksViewMode.FLAT)

        act_category.triggered.connect(
            lambda: self._set_available_view_mode(ChecksViewMode.CATEGORY)
        )
        act_flat.triggered.connect(
            lambda: self._set_available_view_mode(ChecksViewMode.FLAT)
        )
        menu.addAction(act_category)
        menu.addAction(act_flat)
        menu.addSeparator()

        # Expand/collapse actions (only enabled in category view).
        act_expand_all = QAction(
            self.t("checks.expand_all", "Expand all"),
            self,
        )
        act_collapse_all = QAction(
            self.t("checks.collapse_all", "Collapse all"),
            self,
        )
        act_expand_all.triggered.connect(self.c_available.expandAll)
        act_collapse_all.triggered.connect(self.c_available.collapseAll)
        act_expand_all.setEnabled(mode == ChecksViewMode.CATEGORY)
        act_collapse_all.setEnabled(mode == ChecksViewMode.CATEGORY)
        menu.addAction(act_expand_all)
        menu.addAction(act_collapse_all)
        menu.addSeparator()

        # Sorting.
        act_sort_asc = QAction(
            self.t("checks.sort.asc", "Sort by title (A→Z)"),
            self,
        )
        act_sort_desc = QAction(
            self.t("checks.sort.desc", "Sort by title (Z→A)"),
            self,
        )
        act_sort_asc.triggered.connect(
            lambda: self.available_model.sort(0, Qt.SortOrder.AscendingOrder)
        )
        act_sort_desc.triggered.connect(
            lambda: self.available_model.sort(0, Qt.SortOrder.DescendingOrder)
        )
        menu.addAction(act_sort_asc)
        menu.addAction(act_sort_desc)

        menu.exec_(self.c_available.viewport().mapToGlobal(pos))

    def _on_selected_context_menu(self, pos) -> None:
        """Show context menu for the selected checks view.

        Args:
            pos: Position where the menu is requested.
        """
        menu = QMenu(self)

        # Remove selected.
        act_remove = QAction(self.t("checks.remove", "Remove selected"), self)
        act_remove.triggered.connect(self._on_remove_clicked)
        menu.addAction(act_remove)
        menu.addSeparator()

        # View mode.
        act_category = QAction(
            self.t("checks.view.category", "Category view"),
            self,
        )
        act_category.setCheckable(True)
        act_flat = QAction(self.t("checks.view.flat", "Flat view"), self)
        act_flat.setCheckable(True)

        mode = self.selected_model.get_view_mode()
        act_category.setChecked(mode == ChecksViewMode.CATEGORY)
        act_flat.setChecked(mode == ChecksViewMode.FLAT)

        act_category.triggered.connect(
            lambda: self._set_selected_view_mode(ChecksViewMode.CATEGORY)
        )
        act_flat.triggered.connect(
            lambda: self._set_selected_view_mode(ChecksViewMode.FLAT)
        )
        menu.addAction(act_category)
        menu.addAction(act_flat)
        menu.addSeparator()

        # Expand/collapse actions (only enabled in category view).
        act_expand_all = QAction(
            self.t("checks.expand_all", "Expand all"),
            self,
        )
        act_collapse_all = QAction(
            self.t("checks.collapse_all", "Collapse all"),
            self,
        )
        act_expand_all.triggered.connect(self.c_selected.expandAll)
        act_collapse_all.triggered.connect(self.c_selected.collapseAll)
        act_expand_all.setEnabled(mode == ChecksViewMode.CATEGORY)
        act_collapse_all.setEnabled(mode == ChecksViewMode.CATEGORY)
        menu.addAction(act_expand_all)
        menu.addAction(act_collapse_all)
        menu.addSeparator()

        # Sorting.
        act_sort_asc = QAction(
            self.t("checks.sort.asc", "Sort by title (A→Z)"),
            self,
        )
        act_sort_desc = QAction(
            self.t("checks.sort.desc", "Sort by title (Z→A)"),
            self,
        )
        act_sort_asc.triggered.connect(
            lambda: self.selected_model.sort(0, Qt.SortOrder.AscendingOrder)
        )
        act_sort_desc.triggered.connect(
            lambda: self.selected_model.sort(0, Qt.SortOrder.DescendingOrder)
        )
        menu.addAction(act_sort_asc)
        menu.addAction(act_sort_desc)

        menu.exec_(self.c_selected.viewport().mapToGlobal(pos))

    def _on_refresh_available(self) -> None:
        """Reload available checks and re-apply exclusions."""
        try:
            self.available_model.reload_checks()
            self._sync_models()
        except Exception as e:
            QMessageBox.critical(
                self,
                self.t("checks.refresh.error.title", "Error"),
                self.t(
                    "checks.refresh.error.msg",
                    "Failed to refresh checks: {error}",
                    error=str(e),
                ),
            )

    def _set_available_view_mode(self, mode: ChecksViewMode) -> None:
        """Change available model view mode.

        Args:
            mode: Mode to apply to the available view.
        """
        self.available_model.set_view_mode(mode)
        self._apply_view_mode_to_view(self.c_available, mode)

    def _set_selected_view_mode(self, mode: ChecksViewMode) -> None:
        """Change selected model view mode.

        Args:
            mode: Mode to apply to the selected view.
        """
        self.selected_model.set_view_mode(mode)
        self._apply_view_mode_to_view(self.c_selected, mode)

    def _on_add_clicked(self) -> None:
        """Move selected checks from available to selected."""
        if self._state == TaskState.RUNNING:
            return
        avail_state = self._snapshot_category_state(self.c_available)
        sel_state = self._snapshot_category_state(self.c_selected)

        sel = self.c_available.selectionModel()
        if sel is None:
            return

        checks = self.available_model.checks_from_indexes(sel.selectedRows(0))
        if not checks:
            return

        ids = {chk.check_id for chk in checks}
        taken = self.available_model.take_checks_by_id(ids)
        self.selected_model.add_checks(taken)
        self._sync_models()
        self._rebuild_parameter_pages()

        self._restore_category_state(self.c_available, *avail_state)
        self._restore_category_state(self.c_selected, *sel_state)
        self._select_check_ids(self.c_selected, ids)

    def _on_available_double_clicked(self, index: QModelIndex) -> None:
        """Move a check (or a whole category) from available to selected.

        Args:
            index: Double-clicked index in the available view.
        """
        if not index.isValid():
            return
        if self._state == TaskState.RUNNING:
            return

        avail_state = self._snapshot_category_state(self.c_available)
        sel_state = self._snapshot_category_state(self.c_selected)

        checks = self.available_model.checks_from_indexes([index])
        if not checks:
            return

        ids = {chk.check_id for chk in checks}
        taken = self.available_model.take_checks_by_id(ids)
        self.selected_model.add_checks(taken)
        self._sync_models()
        self._rebuild_parameter_pages()

        self._restore_category_state(self.c_available, *avail_state)
        self._restore_category_state(self.c_selected, *sel_state)
        self._select_check_ids(self.c_selected, ids)

    def _on_remove_clicked(self) -> None:
        """Move selected checks from selected back to available."""
        if self._state == TaskState.RUNNING:
            return
        avail_state = self._snapshot_category_state(self.c_available)
        sel_state = self._snapshot_category_state(self.c_selected)

        sel = self.c_selected.selectionModel()
        if sel is None:
            return

        checks = self.selected_model.checks_from_indexes(sel.selectedRows(0))
        if not checks:
            return

        ids = {chk.check_id for chk in checks}
        removed = self.selected_model.remove_checks_by_id(ids)
        self.available_model.put_back_checks(removed)
        self._sync_models()
        self._rebuild_parameter_pages()

        self._restore_category_state(self.c_available, *avail_state)
        self._restore_category_state(self.c_selected, *sel_state)
        self._select_check_ids(self.c_available, ids)

    def _on_selected_double_clicked(self, index: QModelIndex) -> None:
        """Move a check (or a whole category) from selected back to available.

        Args:
            index: Double-clicked index in the selected view.
        """
        if not index.isValid():
            return
        if self._state == TaskState.RUNNING:
            return

        avail_state = self._snapshot_category_state(self.c_available)
        sel_state = self._snapshot_category_state(self.c_selected)

        checks = self.selected_model.checks_from_indexes([index])
        if not checks:
            return

        ids = {chk.check_id for chk in checks}
        removed = self.selected_model.remove_checks_by_id(ids)
        self.available_model.put_back_checks(removed)
        self._sync_models()
        self._rebuild_parameter_pages()

        self._restore_category_state(self.c_available, *avail_state)
        self._restore_category_state(self.c_selected, *sel_state)
        self._select_check_ids(self.c_available, ids)

    def _snapshot_category_state(
        self, view: QWidget
    ) -> Tuple[set[str], set[str]]:
        """Snapshot expanded/collapsed state for top-level categories.

        Args:
            view: A QTreeView-like widget.

        Returns:
            Tuple(expanded_titles, existing_titles).
        """
        model = getattr(view, "model", lambda: None)()
        if model is None or getattr(model, "get_view_mode", None) is None:
            return set(), set()
        if model.get_view_mode() != ChecksViewMode.CATEGORY:
            return set(), set()

        expanded: set[str] = set()
        existing: set[str] = set()
        root = QModelIndex()
        for row in range(model.rowCount(root)):
            idx = model.index(row, 0, root)
            is_category = bool(idx.data(Qt.ItemDataRole.UserRole + 3))
            if not is_category:
                continue

            title = str(idx.data(Qt.ItemDataRole.DisplayRole) or "")
            existing.add(title)
            if view.isExpanded(idx):
                expanded.add(title)
        return expanded, existing

    def _restore_category_state(
        self,
        view: QWidget,
        expanded_titles: set[str],
        existing_titles: set[str],
    ) -> None:
        """Restore expanded/collapsed state for top-level categories.

        New categories (not present in ``existing_titles``) default to expanded.

        Args:
            view: A QTreeView-like widget.
            expanded_titles: Titles to expand.
            existing_titles: Titles that existed when snapshot was taken.
        """
        model = getattr(view, "model", lambda: None)()
        if model is None or getattr(model, "get_view_mode", None) is None:
            return
        if model.get_view_mode() != ChecksViewMode.CATEGORY:
            return

        root = QModelIndex()
        for row in range(model.rowCount(root)):
            idx = model.index(row, 0, root)
            is_category = bool(idx.data(Qt.ItemDataRole.UserRole + 3))
            if not is_category:
                continue

            title = str(idx.data(Qt.ItemDataRole.DisplayRole) or "")
            should_expand = (
                title in expanded_titles or title not in existing_titles
            )
            if should_expand:
                view.expand(idx)
            else:
                view.collapse(idx)

    def _select_check_ids(self, view: QWidget, ids: set[str]) -> None:
        """Select checks by id in the given view.

        Args:
            view: A QTreeView-like widget.
            ids: Check ids to select.
        """
        if not ids:
            return

        model = getattr(view, "model", lambda: None)()
        sel_model = getattr(view, "selectionModel", lambda: None)()
        if model is None or sel_model is None:
            return

        # Collect model indexes for the requested checks.
        targets: List[QModelIndex] = []
        root = QModelIndex()
        for row in range(model.rowCount(root)):
            idx = model.index(row, 0, root)
            check_id = str(idx.data(Qt.ItemDataRole.UserRole + 4) or "")
            if check_id and check_id in ids:
                targets.append(idx)
                continue

            is_category = bool(idx.data(Qt.ItemDataRole.UserRole + 3))
            if not is_category:
                continue

            for crow in range(model.rowCount(idx)):
                c_idx = model.index(crow, 0, idx)
                cid = str(c_idx.data(Qt.ItemDataRole.UserRole + 4) or "")
                if cid and cid in ids:
                    targets.append(c_idx)

        if not targets:
            return

        # Apply the selection.
        selection = QItemSelection()
        for idx in targets:
            selection.select(idx, idx)
        sel_model.clearSelection()
        sel_model.select(
            selection,
            QItemSelectionModel.SelectionFlag.ClearAndSelect
            | QItemSelectionModel.SelectionFlag.Rows,
        )
        view.scrollTo(targets[0])

    def _sync_models(self) -> None:
        """Keep models consistent (available excludes selected)."""
        self.available_model.set_excluded_check_ids(
            self.selected_model.get_check_ids()
        )

    def _on_state_changed(self) -> None:
        """Handle parameter widget state changes.

        Parameter widgets expect a runner-like object exposing this method.
        """

    def _rebuild_parameter_pages(self) -> None:
        """Rebuild parameter pages for the currently selected checks."""
        self._clear_parameter_pages()

        checks = self.selected_model.get_checks()
        if not checks:
            self._reset_tab_group(parameter_buttons=0)
            return

        # Deduplicate parameters and unify shared parameter instances.
        params_by_key: Dict[Tuple[str, str], "TaskParameter"] = {}
        for chk in checks:
            for param in chk.parameters.values():
                key = (param.category or "", param.name)
                if key in params_by_key:
                    # Unify by re-pointing this check to the shared parameter.
                    chk.parameters[param.name] = params_by_key[key]
                else:
                    params_by_key[key] = param

        # Group parameters by category (stable insertion order).
        grouped: Dict[str, OrderedDict[str, "TaskParameter"]] = defaultdict(
            OrderedDict
        )
        for (category, name), param in params_by_key.items():
            grouped[category][name] = param

        # Normalize category ordering similar to TaskRunner.
        categories = OrderedDict(grouped)
        default_name = self.t("task.parameters", "Parameters")

        default_categ: OrderedDict[str, "TaskParameter"] = OrderedDict()
        if default_name in categories:
            default_categ.update(categories[default_name])
            del categories[default_name]

        if None in categories:  # type: ignore[comparison-overlap]
            default_categ.update(categories[None])  # type: ignore[index]
            del categories[None]  # type: ignore[index]
        if "" in categories:
            default_categ.update(categories[""])
            del categories[""]

        # Always include the default category page.
        ordered_categories: List[
            Tuple[str, OrderedDict[str, "TaskParameter"]]
        ] = []
        ordered_categories.append((default_name, default_categ))
        ordered_categories.extend(list(categories.items()))

        # Ensure page_results is last.
        self.c_stacked.removeWidget(self.page_results)

        # Create and insert pages + tab buttons.
        b_index = 1
        for title, controls in ordered_categories:
            page = self._create_page_for_parameters(title, controls)
            self.c_stacked.insertWidget(b_index, page)
            self._param_pages.append(page)

            btn = QPushButton(title, self)
            btn.setCheckable(True)
            self.lay_tab.insertWidget(2, btn)
            self._param_tab_buttons.append(btn)
            b_index += 1

        # Re-add results page at the end.
        self.c_stacked.addWidget(self.page_results)

        # Rebuild the tab group IDs and keep checks tab selected.
        self._reset_tab_group(parameter_buttons=len(self._param_tab_buttons))
        self.c_checks_tab.setChecked(True)
        self.c_stacked.setCurrentIndex(0)

    def _reset_tab_group(self, parameter_buttons: int) -> None:
        """Reset tab ids so they map to the current stacked page indices.

        Args:
            parameter_buttons: Number of parameter tab buttons present.
        """
        old_group = getattr(self, "_tab_group", None)
        if old_group is not None:
            old_group.deleteLater()

        self._tab_group = QButtonGroup(self)
        self._tab_group.setExclusive(True)

        self._tab_group.addButton(self.c_checks_tab, 0)

        for i, btn in enumerate(self._param_tab_buttons, start=1):
            self._tab_group.addButton(btn, i)

        self._tab_group.addButton(self.c_results_tab, parameter_buttons + 1)
        self._tab_group.idClicked.connect(self.c_stacked.setCurrentIndex)

    def _clear_parameter_pages(self) -> None:
        """Remove parameter pages and buttons inserted into the UI."""
        # Remove parameter pages (keeps page_checks/page_results intact).
        for page in self._param_pages:
            self.c_stacked.removeWidget(page)
            page.deleteLater()
        self._param_pages = []

        # Remove parameter tab buttons from the layout.
        for btn in self._param_tab_buttons:
            self.lay_tab.removeWidget(btn)
            btn.deleteLater()
        self._param_tab_buttons = []

        # Ensure we only have the two base pages.
        self.c_stacked.setCurrentIndex(0)
        self.c_stacked.removeWidget(self.page_results)
        self.c_stacked.addWidget(self.page_results)

    def _create_page_for_parameters(
        self,
        title: str,
        controls: OrderedDict[str, "TaskParameter"],
    ) -> QWidget:
        """Create a stacked page and populate it with parameter controls.

        Args:
            title: Page title.
            controls: Parameters to show.

        Returns:
            The created page widget.
        """
        default_name = self.t("task.parameters", "Parameters")
        if title != default_name:
            return self.create_parameters_page(controls, parent=self)

        # Default parameters page: DB connection first, then parameters.
        page = QWidget(self)
        lay = QFormLayout()
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(2)
        page.setLayout(lay)

        # Create the DB connection control.
        self._db_connection = ChooseDb(parent=page, ctx=self.ctx)
        self._db_connection.populate_db_connections()
        lay.addRow(self.t("checks.db", "Database"), self._db_connection)

        # Add parameter controls.
        label_font = None
        for parameter in controls.values():
            lay.addRow(
                parameter.title,
                self.create_control_for_parameter(parameter),
            )

            if parameter.description:
                lbl = QLabel(parameter.description, page)
                lbl.setWordWrap(True)
                if label_font is None:
                    label_font = lbl.font()
                    label_font.setItalic(True)
                lbl.setFont(label_font)
                lbl.setContentsMargins(0, 0, 0, 2)
                lay.addRow(lbl)

        return page
