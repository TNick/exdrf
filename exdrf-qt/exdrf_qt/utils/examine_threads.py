import logging
from collections import deque
from datetime import datetime
from typing import TYPE_CHECKING, Any, Deque, Optional, cast

import sqlparse  # type: ignore
from PyQt5.QtCore import (
    QAbstractItemModel,
    QAbstractListModel,
    QItemSelection,
    QItemSelectionModel,
    QModelIndex,
    QObject,
    QRect,
    QSize,
    Qt,
    QTimer,
)
from PyQt5.QtGui import QColor, QIcon, QPainter, QPalette
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListView,
    QMenu,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext

logger = logging.getLogger(__name__)


def _format_duration_s(val: Any) -> str:
    """Format a duration in seconds rounded to 2 decimals.

    Args:
        val: Duration in seconds.

    Returns:
        A human readable duration string.
    """
    if val is None:
        return "-"
    try:
        return "%.2fs" % float(val)
    except Exception as e:
        logger.exception("Invalid duration value %s: %s", val, e)
        return "-"


def _humanize_ts(val: Any) -> str:
    """Humanize a unix timestamp into local time + relative age.

    Args:
        val: Unix timestamp (seconds since epoch).

    Returns:
        A human readable timestamp like "2026-01-25 12:34:56 (3m 10s ago)".
    """
    if val is None:
        return "-"
    try:
        ts = float(val)
    except Exception as e:
        logger.exception("Invalid timestamp value %s: %s", val, e)
        return "-"

    dt = datetime.fromtimestamp(ts)
    now = datetime.now()
    delta_s = (now - dt).total_seconds()
    future = delta_s < 0
    delta_s = abs(delta_s)

    seconds = int(delta_s)
    mins, sec = divmod(seconds, 60)
    hrs, mins = divmod(mins, 60)
    days, hrs = divmod(hrs, 24)

    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hrs:
        parts.append(f"{hrs}h")
    if mins and not days:
        parts.append(f"{mins}m")
    if (sec or not parts) and not days and hrs < 4:
        parts.append(f"{sec}s")

    rel = " ".join(parts)
    if future:
        rel = f"in {rel}"
    else:
        rel = f"{rel} ago"

    return "%s (%s)" % (dt.strftime("%Y-%m-%d %H:%M:%S"), rel)


def _format_sql(sql: Any) -> str:
    """Format SQL text for display/copy.

    Args:
        sql: SQL string or object convertible to string.

    Returns:
        Formatted SQL string.
    """
    if sql is None:
        return ""

    try:
        txt = str(sql)
        pretty_sql = sqlparse.format(
            txt,
            reindent=True,
            keyword_case="upper",
        ).replace(" ON ", "\n    ON ")
        return pretty_sql
    except Exception as e:
        logger.exception("Failed to format SQL: %s", e)
        return str(sql)


class WorkerListModel(QAbstractListModel):
    """List model for worker threads.

    The model stores worker snapshots retrieved from a relay debug snapshot.
    This is intentionally not based on QStandardItemModel.

    Attributes:
        _items: Current list of worker snapshot dictionaries.
    """

    ROLE_WORKER = Qt.ItemDataRole.UserRole + 1
    ROLE_WORKER_ID = Qt.ItemDataRole.UserRole + 2

    _items: list[dict[str, Any]]

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._items = []

    def rowCount(
        self, parent: QModelIndex = QModelIndex()
    ) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(self._items)

    def data(
        self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:  # noqa: E501, N802
        if not index.isValid():
            return None

        row = index.row()
        if row < 0 or row >= len(self._items):
            return None

        item = self._items[row]
        if role == self.ROLE_WORKER:
            return item
        if role == self.ROLE_WORKER_ID:
            return item.get("id")
        if role == Qt.ItemDataRole.DisplayRole:
            # Used only for accessibility/fallback rendering.
            return item.get("object_name") or f"Worker {item.get('id')}"
        if role == Qt.ItemDataRole.ToolTipRole:
            return item.get("_tooltip", "")

        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:  # noqa: N802
        if not index.isValid():
            return cast(Qt.ItemFlags, Qt.ItemFlag.NoItemFlags)

        return cast(
            Qt.ItemFlags,
            Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable,
        )

    def update_from_relay_snapshot(self, snapshot: dict[str, Any]) -> None:
        """Update model contents from a relay snapshot.

        Args:
            snapshot: Result of `Relay.debug_snapshot()`.
        """
        workers = snapshot.get("workers") or []
        if not isinstance(workers, list):
            workers = []

        # Keep order stable and deterministic.
        def _k(w: dict[str, Any]) -> tuple[int, str]:
            wid = w.get("id")
            if wid is None:
                return (0, "")
            try:
                return (int(wid), str(wid))
            except Exception as e:
                logger.log(
                    1,
                    "Non-integer worker id %s: %s",
                    wid,
                    e,
                    exc_info=True,
                )
                return (0, str(wid))

        new_items = [w for w in workers if isinstance(w, dict)]
        new_items.sort(key=_k)

        if len(new_items) != len(self._items):
            self.beginResetModel()
            self._items = new_items
            self.endResetModel()
            return

        self._items = new_items
        if self._items:
            top_left = self.index(0, 0)
            bottom_right = self.index(len(self._items) - 1, 0)
            self.dataChanged.emit(top_left, bottom_right, [])


class WorkerItemDelegate(QStyledItemDelegate):
    """Custom delegate that paints each worker item."""

    ic_running: QIcon
    ic_stopped: QIcon
    ic_waiting: QIcon

    def __init__(
        self, ctx: "QtContext", parent: Optional[QObject] = None
    ) -> None:
        super().__init__(parent)
        self.ctx = ctx

        self.ic_running = ctx.get_icon("fire")
        self.ic_stopped = ctx.get_icon("check_box_uncheck")
        self.ic_waiting = ctx.get_icon("hand")

    def sizeHint(
        self, option: QStyleOptionViewItem, index: QModelIndex
    ) -> QSize:  # noqa: N802, E501
        base = super().sizeHint(option, index)
        return QSize(base.width(), max(base.height(), 54))

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:  # noqa: E501, N802
        # Prepare base style option.
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        style = (
            opt.widget.style()
            if opt.widget is not None
            else QApplication.style()
        )
        style = cast(QStyle, style)

        # Draw the standard item background/selection in a theme-aware way.
        painter.save()
        opt.text = ""
        opt.icon = QIcon()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter)
        # Some styles modify painter state (clip, hints). Restore immediately.
        painter.restore()

        # Now paint custom content with a clean painter state.
        painter.save()

        item = index.data(WorkerListModel.ROLE_WORKER) or {}
        if not isinstance(item, dict):
            item = {}

        # Extract display fields.
        object_name = item.get("object_name") or ""
        is_running = bool(item.get("is_running"))
        req_id = item.get("current_work_req_id")
        category = item.get("current_work_category")
        priority = item.get("current_work_priority")

        stats = item.get("stats") or {}
        if not isinstance(stats, dict):
            stats = {}
        error_count = int(stats.get("error_count") or 0)
        last10 = stats.get("last_10") or {}
        if not isinstance(last10, dict):
            last10 = {}
        avg_s = last10.get("avg_duration_s")
        avg_s_f = float(avg_s) if avg_s is not None else None

        # Compute average speed as works per second.
        avg_speed = None
        if avg_s_f is not None and avg_s_f > 0:
            avg_speed = 1.0 / avg_s_f

        # Layout.
        #
        # IMPORTANT: QRect is mutable in PyQt wrappers; assignment shares the
        # same underlying object. Always copy before mutating, otherwise
        # shrinking icon_rect also shrinks rect and breaks text_rect.
        rect = QRect(opt.rect).adjusted(6, 4, -6, -4)
        icon_size = 18
        icon_rect = QRect(rect)
        icon_rect.setWidth(icon_size)
        icon_rect.setHeight(icon_size)
        icon_rect.moveTop(rect.top() + 4)

        text_rect = QRect(rect).adjusted(icon_size + 8, 0, 0, 0)

        # Reserve a right column only when there is enough horizontal space.
        # Otherwise, paint both left/right aligned texts in the full text rect.
        if text_rect.width() >= 260:
            right_rect = QRect(text_rect)
            right_rect.setLeft(text_rect.right() - 180)
            left_rect = QRect(text_rect)
            left_rect.setRight(right_rect.left() - 8)
        else:
            left_rect = QRect(text_rect)
            right_rect = QRect(text_rect)

        # Pick icon based on worker state.
        #
        # - stopped: thread is not running
        # - waiting: thread is running but not currently processing work
        # - running: thread is running and actively processing a work item
        if not is_running:
            icon = self.ic_stopped
        elif req_id is None:
            icon = self.ic_waiting
        else:
            icon = self.ic_running
        icon.paint(painter, icon_rect)

        # Choose text colors that work with selection/theme.
        is_selected = bool(opt.state & QStyle.StateFlag.State_Selected)
        text_color = opt.palette.color(
            QPalette.ColorRole.HighlightedText
            if is_selected
            else QPalette.ColorRole.Text
        )
        subtle_color = opt.palette.color(
            QPalette.ColorRole.HighlightedText
            if is_selected
            else QPalette.ColorRole.Mid
        )

        # Draw left text (two lines).
        painter.setPen(text_color)
        f = painter.font()
        f.setBold(True)
        painter.setFont(f)
        top_line = object_name or f"Worker {item.get('id')}"
        painter.drawText(
            left_rect.adjusted(0, 0, 0, -24),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            top_line,
        )

        f.setBold(False)
        painter.setFont(f)
        bottom_parts = []
        bottom_parts.append(f"req_id={req_id}")
        bottom_parts.append(f"cat={category}")
        bottom_parts.append(f"pr={priority}")
        painter.setPen(text_color)
        painter.drawText(
            left_rect.adjusted(0, 24, 0, 0),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            " ".join(bottom_parts),
        )

        # Draw right text (avg speed + errors).
        avg_text = "avg: n/a"
        if avg_s_f is not None:
            avg_text = "avg: %.2fms" % (avg_s_f * 1000.0)
            if avg_speed is not None:
                avg_text += " (%.2f/s)" % avg_speed

        painter.setPen(text_color)
        painter.drawText(
            right_rect.adjusted(0, 0, 0, -24),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            avg_text,
        )

        # Errors in red if any.
        if error_count > 0:
            painter.setPen(QColor("#b00020"))
        else:
            painter.setPen(subtle_color)
        painter.drawText(
            right_rect.adjusted(0, 24, 0, 0),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            f"errors: {error_count}",
        )

        painter.restore()


class WorkerDetailsModel(QAbstractItemModel):
    """Detail tree model for the selected worker (2 columns: label/value).

    This is intentionally not based on QStandardItemModel.

    Attributes:
        _root: Root node of the details tree.
        _header: Two column headers.
    """

    class _Node:
        """A node in the details tree.

        Attributes:
            label: Column 0 string.
            value: Column 1 string.
            parent: Parent node, or None for root.
            children: Child nodes.
        """

        label: str
        value: str
        parent: Optional["WorkerDetailsModel._Node"]
        children: list["WorkerDetailsModel._Node"]

        def __init__(
            self,
            label: str,
            value: str = "",
            parent: Optional["WorkerDetailsModel._Node"] = None,
        ) -> None:
            self.label = label
            self.value = value
            self.parent = parent
            self.children = []

        def row(self) -> int:
            if self.parent is None:
                return 0
            try:
                return self.parent.children.index(self)
            except ValueError:
                return 0

    _root: _Node
    _header: tuple[str, str]

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._root = self._Node(label="root")
        self._header = ("Label", "Value")

    def columnCount(
        self, parent: QModelIndex = QModelIndex()
    ) -> int:  # noqa: N802
        _ = parent
        return 2

    def rowCount(
        self, parent: QModelIndex = QModelIndex()
    ) -> int:  # noqa: N802
        node = self._node_from_index(parent)
        return len(node.children)

    def index(  # noqa: N802
        self,
        row: int,
        column: int,
        parent: QModelIndex = QModelIndex(),
    ) -> QModelIndex:
        parent_node = self._node_from_index(parent)
        if row < 0 or row >= len(parent_node.children):
            return QModelIndex()
        if column < 0 or column >= 2:
            return QModelIndex()
        return self.createIndex(row, column, parent_node.children[row])

    def parent(  # noqa: N802
        self, child: QModelIndex = QModelIndex()
    ) -> QModelIndex:
        if not child.isValid():
            return QModelIndex()
        node = self._node_from_index(child)
        if node.parent is None or node.parent is self._root:
            return QModelIndex()
        return self.createIndex(node.parent.row(), 0, node.parent)

    def data(
        self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:  # noqa: E501, N802
        if not index.isValid():
            return None
        node = self._node_from_index(index)
        if role == Qt.ItemDataRole.DisplayRole:
            return node.label if index.column() == 0 else node.value
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:  # noqa: N802
        if not index.isValid():
            return cast(Qt.ItemFlags, Qt.ItemFlag.NoItemFlags)
        return cast(
            Qt.ItemFlags,
            Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable,
        )  # noqa: E501

    def headerData(  # noqa: N802
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation != Qt.Orientation.Horizontal:
            return None
        if section == 0:
            return self._header[0]
        if section == 1:
            return self._header[1]
        return None

    def _node_from_index(self, index: QModelIndex) -> _Node:
        if not index.isValid():
            return self._root
        ptr = index.internalPointer()
        if isinstance(ptr, self._Node):
            return ptr
        return self._root

    def set_tree(self, root: _Node, header: tuple[str, str]) -> None:
        """Replace tree contents.

        Args:
            root: Root node for new tree.
            header: Column headers.
        """
        self.beginResetModel()
        self._root = root
        self._header = header
        self.endResetModel()


class ExamineThreadsWidget(QWidget, QtUseContext):
    """Widget that shows in real time what the threads are doing."""

    ctx: "QtContext"

    _timer: QTimer
    _workers_model: WorkerListModel
    _workers_view: QListView
    _details_model: WorkerDetailsModel
    _details_view: QTreeView
    _selected_worker_id: Any
    _is_paused: bool
    _last_snapshot: Optional[dict[str, Any]]
    _btn_pause: QPushButton
    _btn_copy_dump: QPushButton
    _spin_update_ms: QSpinBox
    _lbl_queue_len: QLabel
    _workers_delegate: WorkerItemDelegate
    _update_ms_debouncer: QTimer
    _pending_update_ms: Optional[int]

    _work_log_order: Deque[Any]
    _work_log: dict[Any, dict[str, Any]]

    def __init__(
        self,
        ctx: "QtContext",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self._selected_worker_id = None
        self._is_paused = False
        self._last_snapshot = None
        self._pending_update_ms = None
        self._work_log_order = deque(maxlen=500)
        self._work_log = {}

        # Initialize timer early so UI controls can bind to it.
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self.refresh)

        # Debounce timer interval changes to avoid thrashing.
        self._update_ms_debouncer = QTimer(self)
        self._update_ms_debouncer.setSingleShot(True)
        self._update_ms_debouncer.setInterval(250)
        self._update_ms_debouncer.timeout.connect(self._apply_pending_update_ms)

        # Build master/detail UI.
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        layout.addWidget(splitter, 1)

        self._workers_model = WorkerListModel(self)
        self._workers_view = QListView(splitter)
        self._workers_view.setModel(self._workers_model)
        self._workers_delegate = WorkerItemDelegate(
            ctx=self.ctx, parent=self._workers_view
        )
        self._workers_view.setItemDelegate(self._workers_delegate)
        self._workers_view.setSelectionMode(
            QListView.SelectionMode.SingleSelection
        )
        self._workers_view.setUniformItemSizes(True)

        self._details_model = WorkerDetailsModel(self)
        self._details_view = QTreeView(splitter)
        self._details_view.setModel(self._details_model)
        self._details_view.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        self._details_view.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._details_view.setRootIsDecorated(False)
        self._details_view.setItemsExpandable(True)
        self._details_view.setUniformRowHeights(True)
        self._details_view.setAllColumnsShowFocus(True)

        # Support context menu on worker list.
        self._workers_view.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self._workers_view.customContextMenuRequested.connect(
            self._on_worker_context_menu
        )

        splitter.addWidget(self._workers_view)
        splitter.addWidget(self._details_view)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        # Add bottom button row.
        btn_frame = QFrame(self)
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)

        self._btn_pause = QPushButton(self)
        self._btn_pause.setText("Pause")
        self._btn_pause.clicked.connect(self._toggle_pause)
        btn_layout.addWidget(self._btn_pause)

        self._spin_update_ms = QSpinBox(self)
        self._spin_update_ms.setRange(100, 60000)
        self._spin_update_ms.setSingleStep(100)
        self._spin_update_ms.setSuffix(" ms")
        self._spin_update_ms.setValue(self._timer.interval())
        self._spin_update_ms.valueChanged.connect(self._on_update_ms_changed)
        btn_layout.addWidget(self._spin_update_ms)

        self._lbl_queue_len = QLabel(self)
        self._lbl_queue_len.setText("Queue: -")
        btn_layout.addWidget(self._lbl_queue_len)

        btn_layout.addStretch(1)

        self._btn_copy_dump = QPushButton(self)
        self._btn_copy_dump.setText("Copy dump")
        self._btn_copy_dump.clicked.connect(self._copy_dump_to_clipboard)
        btn_layout.addWidget(self._btn_copy_dump)

        layout.addWidget(btn_frame, 0)

        # React to selection changes.
        self._workers_view.selectionModel().selectionChanged.connect(
            self._on_worker_selected
        )

        # Start polling.
        self._timer.start()

        self.refresh()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Stop polling when the widget is closed."""
        try:
            self._timer.stop()
        except Exception as e:
            logger.log(
                1,
                "Failed to stop ExamineThreadsWidget timer: %s",
                e,
                exc_info=True,
            )
        super().closeEvent(event)

    def _toggle_pause(self) -> None:
        """Toggle polling pause/resume."""
        self._is_paused = not self._is_paused
        if self._is_paused:
            self._btn_pause.setText("Resume")
            self._timer.stop()
        else:
            self._btn_pause.setText("Pause")
            self._timer.start()
            self.refresh()

    def _on_update_ms_changed(self, value: int) -> None:
        """Debounced handler for polling interval changes.

        Args:
            value: New interval in milliseconds.
        """
        self._pending_update_ms = value
        self._update_ms_debouncer.start()

    def _apply_pending_update_ms(self) -> None:
        """Apply the last interval change after debounce."""
        if self._pending_update_ms is None:
            return

        self._timer.setInterval(self._pending_update_ms)

    def _copy_dump_to_clipboard(self) -> None:
        """Copy the latest relay dump to clipboard."""
        snapshot = self._last_snapshot
        if snapshot is None:
            dump = "No relay snapshot available."
        else:
            dump = self._format_snapshot_dump(snapshot)

        try:
            cb = QApplication.clipboard()
            if cb is None:
                logger.error("Clipboard is not available")
                return
            cb.setText(dump)
        except Exception as e:
            logger.error(
                "Failed to copy dump to clipboard: %s", e, exc_info=True
            )

    def _format_snapshot_dump(self, snapshot: dict[str, Any]) -> str:
        """Format a detailed snapshot as copyable text.

        Args:
            snapshot: The relay debug snapshot.

        Returns:
            A human-readable multi-line string.
        """
        lines: list[str] = []
        lines.append(
            "Examine threads (dump @ %s)"
            % datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        lines.append("")

        q = snapshot.get("queue") or {}
        if not isinstance(q, dict):
            q = {}
        lines.append("Queue")
        lines.append("  total_len: %s" % q.get("total_len"))
        lines.append("  class_order: %s" % q.get("class_order"))
        lines.append("  sizes_by_class: %s" % q.get("sizes_by_class"))
        lines.append("")

        lines.append("Workers")
        workers = snapshot.get("workers") or []
        if not isinstance(workers, list):
            workers = []
        for w in workers:
            if not isinstance(w, dict):
                continue
            lines.append("")
            lines.append("Worker %s" % w.get("id"))
            lines.append("  object_name: %s" % w.get("object_name"))
            lines.append("  is_running: %s" % w.get("is_running"))
            lines.append("  should_stop: %s" % w.get("should_stop"))
            lines.append(
                "  current_work_req_id: %s" % w.get("current_work_req_id")
            )
            lines.append(
                "  current_work_category: %s" % w.get("current_work_category")
            )
            lines.append(
                "  current_work_priority: %s" % w.get("current_work_priority")
            )

            st = w.get("stats") or {}
            if not isinstance(st, dict):
                st = {}
            cur = st.get("current") or {}
            if not isinstance(cur, dict):
                cur = {}
            last10 = st.get("last_10") or {}
            if not isinstance(last10, dict):
                last10 = {}

            lines.append("  stats")
            lines.append("    started_count: %s" % st.get("started_count"))
            lines.append("    finished_count: %s" % st.get("finished_count"))
            lines.append("    error_count: %s" % st.get("error_count"))
            lines.append(
                "    last_started_at: %s"
                % _humanize_ts(st.get("last_started_at"))
            )  # noqa: E501
            lines.append(
                "    last_finished_at: %s"
                % _humanize_ts(st.get("last_finished_at"))
            )  # noqa: E501
            lines.append("    current")
            lines.append("      req_id: %s" % cur.get("req_id"))
            lines.append("      category: %s" % cur.get("category"))
            lines.append("      priority: %s" % cur.get("priority"))
            lines.append(
                "      elapsed_s: %s" % _format_duration_s(cur.get("elapsed_s"))
            )
            lines.append("    last_10")
            durs = last10.get("durations_s") or []
            if isinstance(durs, list):
                durs_fmt = [_format_duration_s(x) for x in durs]
            else:
                durs_fmt = []
            lines.append("      durations_s: %s" % durs_fmt)
            lines.append(
                "      avg_duration_s: %s"
                % _format_duration_s(last10.get("avg_duration_s"))
            )
            lines.append("      history:")
            hist = last10.get("history") or []
            if not isinstance(hist, list):
                hist = []
            for h in hist:
                if not isinstance(h, dict):
                    continue
                lines.append(
                    "        - req_id=%s cat=%s pr=%s dur=%s results=%s err=%s"
                    % (
                        h.get("req_id"),
                        h.get("category"),
                        h.get("priority"),
                        _format_duration_s(h.get("duration_s")),
                        h.get("results_count"),
                        h.get("had_error"),
                    )
                )
                sp = h.get("statement_preview")
                if sp:
                    lines.append("          statement: %s" % sp)

        return "\n".join(lines)

    def _remember_work_from_snapshot(self, snapshot: dict[str, Any]) -> None:
        """Update the widget-side log of observed requests.

        Args:
            snapshot: The relay debug snapshot.
        """
        workers = snapshot.get("workers") or []
        if not isinstance(workers, list):
            return

        for w in workers:
            if not isinstance(w, dict):
                continue

            # Record current work as soon as it is observed.
            cur_req_id = w.get("current_work_req_id")
            if cur_req_id is not None and cur_req_id not in self._work_log:
                raw_sql = w.get("current_work_statement")
                entry = {
                    "req_id": cur_req_id,
                    "category": w.get("current_work_category"),
                    "priority": w.get("current_work_priority"),
                    "finished_at": None,
                    "had_error": None,
                    "results_count": None,
                    "statement_raw": raw_sql,
                    "statement_pretty": _format_sql(raw_sql) if raw_sql else "",
                }
                self._work_log[cur_req_id] = entry
                self._work_log_order.append(cur_req_id)

            stats = w.get("stats") or {}
            if not isinstance(stats, dict):
                continue
            last10 = stats.get("last_10") or {}
            if not isinstance(last10, dict):
                continue
            hist = last10.get("history") or []
            if not isinstance(hist, list):
                continue

            for h in hist:
                if not isinstance(h, dict):
                    continue
                req_id = h.get("req_id")
                if req_id is None:
                    continue
                if req_id in self._work_log:
                    # If we previously recorded a "current" entry, upgrade it
                    # with the finished information when it becomes available.
                    entry = self._work_log.get(req_id, {})
                    entry.update(
                        {
                            "category": h.get("category"),
                            "priority": h.get("priority"),
                            "finished_at": h.get("finished_at"),
                            "had_error": h.get("had_error"),
                            "results_count": h.get("results_count"),
                            "statement_raw": h.get("statement_preview"),
                            "statement_pretty": _format_sql(
                                h.get("statement_preview")
                            ),
                        }
                    )
                    continue

                entry = {
                    "req_id": req_id,
                    "category": h.get("category"),
                    "priority": h.get("priority"),
                    "finished_at": h.get("finished_at"),
                    "had_error": h.get("had_error"),
                    "results_count": h.get("results_count"),
                    "statement_raw": h.get("statement_preview"),
                    "statement_pretty": _format_sql(h.get("statement_preview")),
                }
                self._work_log[req_id] = entry
                self._work_log_order.append(req_id)

        # Trim dict to match deque.
        max_len = self._work_log_order.maxlen or 0
        if len(self._work_log) > max_len and max_len > 0:
            keep = set(self._work_log_order)
            self._work_log = {
                k: v for k, v in self._work_log.items() if k in keep
            }

    def _sql_for_req_id(self, req_id: Any, fallback_raw_sql: Any = None) -> str:
        """Get formatted SQL for a request id, if available.

        Args:
            req_id: The request id.
            fallback_raw_sql: SQL text to format if the id is not in the log.

        Returns:
            Formatted SQL string (possibly empty).
        """
        if req_id is None:
            return _format_sql(fallback_raw_sql) if fallback_raw_sql else ""

        entry = self._work_log.get(req_id)
        if entry is not None:
            return entry.get("statement_pretty") or ""

        if fallback_raw_sql:
            return _format_sql(fallback_raw_sql)

        return ""

    def _results_count_for_req_id(self, req_id: Any) -> Optional[int]:
        """Get the result item count for a request id, if available.

        Args:
            req_id: The request id.

        Returns:
            The number of result items, or None if unknown/not completed.
        """
        if req_id is None:
            return None
        entry = self._work_log.get(req_id)
        if entry is None:
            return None
        val = entry.get("results_count")
        if val is None:
            return None
        try:
            return int(val)
        except Exception as e:
            logger.log(
                1,
                "Invalid results_count %s for req_id %s: %s",
                val,
                req_id,
                e,
                exc_info=True,
            )
            return None

    def _on_worker_context_menu(self, pos) -> None:
        """Show context menu for copying formatted SQL."""
        idx = self._workers_view.indexAt(pos)
        if not idx.isValid():
            return

        worker = idx.data(WorkerListModel.ROLE_WORKER)
        if not isinstance(worker, dict):
            return

        req_id = worker.get("current_work_req_id")
        raw_sql = worker.get("current_work_statement")
        pretty_sql = self._sql_for_req_id(req_id, fallback_raw_sql=raw_sql)
        results_count = self._results_count_for_req_id(req_id)

        # Fallback: if there is no current SQL, use the latest completed work.
        if not pretty_sql:
            stats = worker.get("stats") or {}
            if isinstance(stats, dict):
                last10 = stats.get("last_10") or {}
                if isinstance(last10, dict):
                    hist = last10.get("history") or []
                    if isinstance(hist, list) and hist:
                        last = hist[-1]
                        if isinstance(last, dict):
                            pretty_sql = _format_sql(
                                last.get("statement_preview")
                            )

        menu = QMenu(self._workers_view)
        act_copy_sql = menu.addAction("Copy formatted SQL")
        act_copy_info = menu.addAction("Copy request info")
        act = menu.exec_(self._workers_view.viewport().mapToGlobal(pos))
        if act is None:
            return

        if act == act_copy_sql:
            if not pretty_sql:
                logger.log(
                    1,
                    "No formatted SQL for req_id=%s, copying empty string",
                    req_id,
                )
                pretty_sql = ""
            cb = QApplication.clipboard()
            if cb is None:
                logger.error("Clipboard is not available")
                return
            cb.setText(pretty_sql)

        if act == act_copy_info:
            info = "req_id=%s cat=%s pr=%s results=%s" % (
                req_id,
                worker.get("current_work_category"),
                worker.get("current_work_priority"),
                results_count if results_count is not None else "-",
            )
            if pretty_sql:
                info += "\n\n" + pretty_sql
            cb = QApplication.clipboard()
            if cb is None:
                logger.error("Clipboard is not available")
                return
            cb.setText(info)

    def _on_worker_selected(
        self,
        selected: QItemSelection,
        deselected: QItemSelection,
    ) -> None:
        """Update detail list when user selects a worker."""
        _ = deselected

        indexes = selected.indexes()
        if not indexes:
            self._selected_worker_id = None
            self._details_model.set_tree(
                self._build_details_tree(None),
                self._details_header(),
            )
            self._details_view.expandAll()
            return

        idx = indexes[0]
        worker_id = idx.data(WorkerListModel.ROLE_WORKER_ID)
        self._selected_worker_id = worker_id
        worker = idx.data(WorkerListModel.ROLE_WORKER)
        if not isinstance(worker, dict):
            worker = None
        self._details_model.set_tree(
            self._build_details_tree(worker),
            self._details_header(),
        )
        self._details_view.expandAll()

    def refresh(self) -> None:
        """Refresh the displayed thread/worker information."""
        if self._is_paused:
            return

        relay = getattr(self.ctx, "work_relay", None)
        if relay is None:
            self._workers_model.update_from_relay_snapshot({"workers": []})
            self._details_model.set_tree(
                self._build_details_tree(None),
                self._details_header(),
            )
            self._details_view.expandAll()
            self._last_snapshot = None
            self._lbl_queue_len.setText("Queue: -")
            return

        # Collect a detailed snapshot from the relay.
        try:
            snapshot = relay.debug_snapshot()
            self._last_snapshot = snapshot
        except Exception as e:
            logger.error(
                "Failed to read relay debug snapshot: %s",
                e,
                exc_info=True,
            )
            self._workers_model.update_from_relay_snapshot({"workers": []})
            self._details_model.set_tree(
                self._build_details_tree(None),
                self._details_header(),
            )
            self._details_view.expandAll()
            self._last_snapshot = None
            self._lbl_queue_len.setText("Queue: -")
            return

        # Update queue size label in the bottom bar.
        q = snapshot.get("queue") or {}
        if isinstance(q, dict):
            self._lbl_queue_len.setText("Queue: %s" % q.get("total_len"))
        else:
            self._lbl_queue_len.setText("Queue: -")

        # Update widget-level request log.
        self._remember_work_from_snapshot(snapshot)

        # Attach tooltips to worker items.
        workers = snapshot.get("workers") or []
        if isinstance(workers, list):
            for w in workers:
                if not isinstance(w, dict):
                    continue
                req_id = w.get("current_work_req_id")
                raw_sql = w.get("current_work_statement")
                pretty_sql = self._sql_for_req_id(
                    req_id, fallback_raw_sql=raw_sql
                )
                results_count = self._results_count_for_req_id(req_id)
                w["_tooltip"] = (
                    "req_id=%s cat=%s pr=%s results=%s\n\n%s"
                    % (
                        req_id,
                        w.get("current_work_category"),
                        w.get("current_work_priority"),
                        results_count if results_count is not None else "-",
                        pretty_sql,
                    )
                ).strip()

        # Update left list model.
        self._workers_model.update_from_relay_snapshot(snapshot)

        # Keep selection stable across refreshes.
        if (
            self._selected_worker_id is None
            and self._workers_model.rowCount() > 0
        ):
            idx0 = self._workers_model.index(0, 0)
            self._workers_view.setCurrentIndex(idx0)
            return

        if self._selected_worker_id is None:
            self._details_model.set_tree(
                self._build_details_tree(None),
                self._details_header(),
            )
            self._details_view.expandAll()
            return

        # Restore selection by worker id.
        for row in range(self._workers_model.rowCount()):
            idx = self._workers_model.index(row, 0)
            if (
                idx.data(WorkerListModel.ROLE_WORKER_ID)
                == self._selected_worker_id
            ):
                sel_model: QItemSelectionModel = (
                    self._workers_view.selectionModel()
                )
                flags = cast(
                    QItemSelectionModel.SelectionFlags,
                    QItemSelectionModel.SelectionFlag.ClearAndSelect
                    | QItemSelectionModel.SelectionFlag.Rows,
                )
                sel_model.setCurrentIndex(idx, flags)
                worker = idx.data(WorkerListModel.ROLE_WORKER)
                if isinstance(worker, dict):
                    self._details_model.set_tree(
                        self._build_details_tree(worker),
                        self._details_header(),
                    )
                else:
                    self._details_model.set_tree(
                        self._build_details_tree(None),
                        self._details_header(),
                    )
                self._details_view.expandAll()
                break

    def _tw(self, key_suffix: str, d: str, **kwargs: Any) -> str:
        """Translate a thread watcher label using `self.t`.

        Args:
            key_suffix: Key suffix appended to "thread_watcher.".
            d: Default English string.
            **kwargs: Formatting args for translated string.

        Returns:
            Translated string.
        """
        return self.t("thread_watcher.%s" % key_suffix, d, **kwargs)

    def _details_header(self) -> tuple[str, str]:
        """Headers for the details view."""
        return (
            self._tw("details.label", "Label"),
            self._tw("details.value", "Value"),
        )

    def _build_details_tree(
        self, worker_snapshot: Optional[dict[str, Any]]
    ) -> WorkerDetailsModel._Node:
        """Build the details tree for the selected worker.

        Args:
            worker_snapshot: A worker entry from `Relay.debug_snapshot()`.

        Returns:
            Root node for the details tree.
        """
        root = WorkerDetailsModel._Node(label="root")

        if worker_snapshot is None:
            root.children.append(
                WorkerDetailsModel._Node(
                    label=self._tw(
                        "details.no_selection", "No worker selected."
                    ),
                    value="",
                    parent=root,
                )
            )
            return root

        # Worker info group.
        g_worker = WorkerDetailsModel._Node(
            label=self._tw("details.worker", "Worker"),
            value="",
            parent=root,
        )
        root.children.append(g_worker)
        g_worker.children.extend(
            [
                WorkerDetailsModel._Node(
                    label=self._tw("details.object_name", "Object name"),
                    value=str(worker_snapshot.get("object_name")),
                    parent=g_worker,
                ),
                WorkerDetailsModel._Node(
                    label=self._tw("details.is_running", "Is running"),
                    value=str(worker_snapshot.get("is_running")),
                    parent=g_worker,
                ),
                WorkerDetailsModel._Node(
                    label=self._tw("details.should_stop", "Should stop"),
                    value=str(worker_snapshot.get("should_stop")),
                    parent=g_worker,
                ),
            ]
        )

        # Current work group.
        req_id = worker_snapshot.get("current_work_req_id")
        g_cur = WorkerDetailsModel._Node(
            label=self._tw("details.current_work", "Current work"),
            value="",
            parent=root,
        )
        root.children.append(g_cur)
        g_cur.children.extend(
            [
                WorkerDetailsModel._Node(
                    label=self._tw("details.req_id", "Request id"),
                    value=str(req_id),
                    parent=g_cur,
                ),
                WorkerDetailsModel._Node(
                    label=self._tw("details.category", "Category"),
                    value=str(worker_snapshot.get("current_work_category")),
                    parent=g_cur,
                ),
                WorkerDetailsModel._Node(
                    label=self._tw("details.priority", "Priority"),
                    value=str(worker_snapshot.get("current_work_priority")),
                    parent=g_cur,
                ),
                WorkerDetailsModel._Node(
                    label=self._tw("details.results_count", "Result count"),
                    value=str(self._results_count_for_req_id(req_id) or "-"),
                    parent=g_cur,
                ),
            ]
        )

        # Stats group.
        st = worker_snapshot.get("stats") or {}
        if not isinstance(st, dict):
            st = {}
        last10 = st.get("last_10") or {}
        if not isinstance(last10, dict):
            last10 = {}

        g_stats = WorkerDetailsModel._Node(
            label=self._tw("details.stats", "Stats"),
            value="",
            parent=root,
        )
        root.children.append(g_stats)
        g_stats.children.extend(
            [
                WorkerDetailsModel._Node(
                    label=self._tw("details.started_count", "Started count"),
                    value=str(st.get("started_count")),
                    parent=g_stats,
                ),
                WorkerDetailsModel._Node(
                    label=self._tw("details.finished_count", "Finished count"),
                    value=str(st.get("finished_count")),
                    parent=g_stats,
                ),
                WorkerDetailsModel._Node(
                    label=self._tw("details.error_count", "Error count"),
                    value=str(st.get("error_count")),
                    parent=g_stats,
                ),
                WorkerDetailsModel._Node(
                    label=self._tw("details.last_started_at", "Last started"),
                    value=_humanize_ts(st.get("last_started_at")),
                    parent=g_stats,
                ),
                WorkerDetailsModel._Node(
                    label=self._tw("details.last_finished_at", "Last finished"),
                    value=_humanize_ts(st.get("last_finished_at")),
                    parent=g_stats,
                ),
            ]
        )

        # Last 10 group.
        g_last = WorkerDetailsModel._Node(
            label=self._tw("details.last_10", "Last 10"),
            value="",
            parent=root,
        )
        root.children.append(g_last)
        g_last.children.append(
            WorkerDetailsModel._Node(
                label=self._tw("details.avg_duration", "Average duration"),
                value=_format_duration_s(last10.get("avg_duration_s")),
                parent=g_last,
            )
        )

        durations = last10.get("durations_s") or []
        if not isinstance(durations, list):
            durations = []
        g_durs = WorkerDetailsModel._Node(
            label=self._tw("details.durations", "Durations"),
            value="",
            parent=g_last,
        )
        g_last.children.append(g_durs)
        for i, d in enumerate(reversed(durations), start=1):
            g_durs.children.append(
                WorkerDetailsModel._Node(
                    label=self._tw(
                        "details.duration_item",
                        "Duration {idx}",
                        idx=i,
                    ),
                    value=_format_duration_s(d),
                    parent=g_durs,
                )
            )

        # Historical last-10 work entries (most detailed view).
        hist = last10.get("history") or []
        if not isinstance(hist, list):
            hist = []
        g_hist = WorkerDetailsModel._Node(
            label=self._tw("details.history", "History"),
            value="",
            parent=g_last,
        )
        g_last.children.append(g_hist)

        # Keep most recent first in the tree.
        for i, h in enumerate(reversed(hist), start=1):
            if not isinstance(h, dict):
                continue

            h_req_id = h.get("req_id")
            h_cat = h.get("category")
            h_pr = h.get("priority")
            h_dur = h.get("duration_s")
            h_res = h.get("results_count")
            h_err = h.get("had_error")
            h_finished_at = h.get("finished_at")
            h_sql = h.get("statement_preview")

            title = "req_id=%s cat=%s pr=%s" % (h_req_id, h_cat, h_pr)
            n = WorkerDetailsModel._Node(
                label=self._tw(
                    "details.history_item",
                    "Work {idx}",
                    idx=i,
                ),
                value=title,
                parent=g_hist,
            )
            g_hist.children.append(n)

            n.children.extend(
                [
                    WorkerDetailsModel._Node(
                        label=self._tw("details.req_id", "Request id"),
                        value=str(h_req_id),
                        parent=n,
                    ),
                    WorkerDetailsModel._Node(
                        label=self._tw("details.category", "Category"),
                        value=str(h_cat),
                        parent=n,
                    ),
                    WorkerDetailsModel._Node(
                        label=self._tw("details.priority", "Priority"),
                        value=str(h_pr),
                        parent=n,
                    ),
                    WorkerDetailsModel._Node(
                        label=self._tw("details.duration", "Duration"),
                        value=_format_duration_s(h_dur),
                        parent=n,
                    ),
                    WorkerDetailsModel._Node(
                        label=self._tw("details.results_count", "Result count"),
                        value=str(h_res),
                        parent=n,
                    ),
                    WorkerDetailsModel._Node(
                        label=self._tw("details.had_error", "Had error"),
                        value=str(h_err),
                        parent=n,
                    ),
                    WorkerDetailsModel._Node(
                        label=self._tw("details.finished_at", "Finished at"),
                        value=_humanize_ts(h_finished_at),
                        parent=n,
                    ),
                    WorkerDetailsModel._Node(
                        label=self._tw("details.sql", "SQL"),
                        value=_format_sql(h_sql),
                        parent=n,
                    ),
                ]
            )

        return root
