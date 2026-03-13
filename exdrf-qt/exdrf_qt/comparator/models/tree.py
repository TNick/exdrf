from __future__ import annotations

import logging
from typing import Any, Optional

from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt
from PySide6.QtGui import QBrush, QColor

from exdrf_qt.comparator.logic.manager import ComparatorManager
from exdrf_qt.comparator.logic.merge import (
    MERGE_METHOD_FIRST_NOT_NULL,
    MERGE_METHOD_MANUAL,
    LeafMergeState,
)
from exdrf_qt.comparator.logic.nodes import (
    BaseNode,
    LeafNode,
    ParentNode,
    Value,
)

logger = logging.getLogger(__name__)


def _qt_int(val: Any, default: int) -> int:
    """Convert Qt enum or int to int (Qt6 uses enums, Qt5 used ints)."""
    if isinstance(val, int):
        return val
    return getattr(val, "value", default)


# Constants to avoid enum attribute typing issues in some stub versions.
DISPLAY_ROLE = _qt_int(getattr(Qt, "DisplayRole", 0), 0)
EDIT_ROLE = _qt_int(getattr(Qt, "EditRole", 2), 2)
BACKGROUND_ROLE = _qt_int(getattr(Qt, "BackgroundRole", 8), 8)
HORIZONTAL = _qt_int(getattr(Qt, "Horizontal", 1), 1)
NO_ITEM_FLAGS = _qt_int(getattr(Qt, "NoItemFlags", 0), 0)
ITEM_IS_ENABLED = _qt_int(getattr(Qt, "ItemIsEnabled", 1), 1)
ITEM_IS_SELECTABLE = _qt_int(getattr(Qt, "ItemIsSelectable", 1 << 1), 1 << 1)
ITEM_IS_EDITABLE = _qt_int(getattr(Qt, "ItemIsEditable", 1 << 2), 1 << 2)
USER_ROLE_INT = _qt_int(getattr(Qt, "UserRole", 0), 0)
HTML_ROLE = USER_ROLE_INT + 1
# Merge column roles (for delegate and display).
MERGE_METHOD_ROLE = USER_ROLE_INT + 2
MERGE_RESULT_ROLE = USER_ROLE_INT + 3
MERGE_OPTIONS_ROLE = USER_ROLE_INT + 4
MERGE_STATE_ROLE = USER_ROLE_INT + 5
MERGE_CONTEXT_ROLE = USER_ROLE_INT + 6


class ComparatorTreeModel(QAbstractItemModel):
    """Qt item model that exposes comparator data as a tree.

    The model merges the per-source trees provided by the manager into a single
    combined tree keyed by each node's `key` (falling back to the `label`
    when the key is empty). The model shows 1 + N columns (or 1 + N + 2 when
    merge_enabled: Method and Result). Only leaf nodes have values and merge
    cells.

    Attributes:
        manager: The comparator manager providing the sources and data.
        root: The combined root node used by the model.
        num_sources: Number of sources provided by the manager.
        merge_enabled: When True, two extra columns (Method, Result) are shown
            and leaves are editable for merge.
    """

    def __init__(
        self,
        manager: ComparatorManager,
        parent: Optional[Any] = None,
        *,
        merge_enabled: bool = False,
    ) -> None:
        super().__init__(parent)

        # Store manager and number of sources.
        self.manager: ComparatorManager = manager
        self.num_sources: int = len(self.manager.sources)
        self.merge_enabled: bool = merge_enabled

        # Use unified tree already built into manager.root by compare().
        self.root: ParentNode = self.manager.root

    def _method_column(self) -> int:
        """Column index for merge method when merge_enabled."""
        return 1 + self.num_sources

    def _result_column(self) -> int:
        """Column index for merge result when merge_enabled."""
        return 2 + self.num_sources

    def _ensure_merge_state(self, node: LeafNode) -> LeafMergeState:
        """Ensure leaf has merge_state; create with default if None."""
        if node.merge_state is None:
            node.merge_state = LeafMergeState(
                selected_method=MERGE_METHOD_FIRST_NOT_NULL
            )
        return node.merge_state

    # Qt model interface
    # --------------------------------------------------------------------- #
    def index(
        self, row: int, column: int, parent: QModelIndex = QModelIndex()
    ) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        parent_node = self._node_from_index(parent)
        child_node = self._child_at(parent_node, row)
        if child_node is None:
            return QModelIndex()
        return self.createIndex(row, column, child_node)

    def parent(  # type: ignore[override]
        self, child: QModelIndex
    ) -> QModelIndex:
        if not child.isValid():
            return QModelIndex()

        node: BaseNode = self._node_from_index(child)
        parent_node = node.parent
        if (
            parent_node is None
            or parent_node is self.root
            and parent_node.parent is None
        ):
            return QModelIndex()

        grandparent = parent_node.parent
        if not isinstance(grandparent, ParentNode):
            return QModelIndex()

        row = self._row_of_child(grandparent, parent_node)
        if row < 0:
            return QModelIndex()
        return self.createIndex(row, 0, parent_node)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.column() > 0:
            return 0
        node = self._node_from_index(parent)
        return node.child_count

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        # One label column + one per source + optionally Method and Result.
        base = 1 + self.num_sources
        if self.merge_enabled:
            base += 2
        return base

    def data(self, index: QModelIndex, role: int = DISPLAY_ROLE) -> Any:
        if not index.isValid():
            return None

        node: BaseNode = self._node_from_index(index)
        column = index.column()

        # Background color: green when equal, orange when partial,
        # red otherwise.
        if role == BACKGROUND_ROLE:
            # Light green, orange, and red tints
            ok_brush = QBrush(QColor(220, 255, 220))
            partial_brush = QBrush(QColor(255, 240, 220))
            bad_brush = QBrush(QColor(255, 220, 220))

            if isinstance(node, LeafNode):
                status = self._leaf_match_status(node)
                if status == "equal":
                    return ok_brush
                if status == "partial":
                    return partial_brush
                return bad_brush
            if isinstance(node, ParentNode):
                return ok_brush if node.mismatch_count == 0 else bad_brush
            return None

        # Provide HTML diff for delegate via custom role
        # (includes first column).
        if role == HTML_ROLE and isinstance(node, LeafNode):
            base_obj = self._value_for_source(node, 0)
            if base_obj is None or not base_obj.exists:
                return None
            base_text = "" if base_obj.value is None else str(base_obj.value)

            if column == 0:
                # Show left-side diff if any other source is a similar mismatch.
                for s_i in range(1, self.num_sources):
                    crt_obj = self._value_for_source(node, s_i)
                    if crt_obj is None or not crt_obj.exists:
                        continue
                    crt_text = (
                        "" if crt_obj.value is None else str(crt_obj.value)
                    )
                    if crt_text != base_text:
                        # Use LeafNode's similarity check and diff methods.
                        if node.is_similar_enough(base_text, crt_text):
                            left_html, _ = node.html_diff(base_text, crt_text)
                            return left_html
                return None

            if column > 0:
                src_idx = column - 1
                crt_obj = self._value_for_source(node, src_idx)
                if crt_obj is None or not crt_obj.exists or crt_obj is base_obj:
                    return None
                crt_text = "" if crt_obj.value is None else str(crt_obj.value)
                if node.is_similar_enough(base_text, crt_text):
                    _, right_html = node.html_diff(base_text, crt_text)
                    return right_html
            return None

        # Merge column roles (for delegate).
        if self.merge_enabled and isinstance(node, LeafNode):
            state = self._ensure_merge_state(node)
            if column == self._method_column():
                if role == MERGE_METHOD_ROLE:
                    return state.selected_method
                if role == MERGE_OPTIONS_ROLE:
                    return self.manager.get_available_merge_methods(node)
                if role == MERGE_STATE_ROLE:
                    return state
                if role == MERGE_CONTEXT_ROLE:
                    return self.manager.get_merge_context(node)
                if role in (DISPLAY_ROLE, EDIT_ROLE):
                    opts = self.manager.get_available_merge_methods(node)
                    for opt in opts:
                        if opt.id == state.selected_method:
                            return opt.label
                    return state.selected_method
            if column == self._result_column():
                if role == MERGE_RESULT_ROLE:
                    return self.manager.resolve_merge_value(node)
                if role == MERGE_STATE_ROLE:
                    return state
                if role == MERGE_CONTEXT_ROLE:
                    return self.manager.get_merge_context(node)
                if role in (DISPLAY_ROLE, EDIT_ROLE):
                    val = self.manager.resolve_merge_value(node)
                    return "" if val is None else str(val)
                return None

        if role not in (DISPLAY_ROLE, EDIT_ROLE):
            return None

        # First column is the node label.
        if column == 0:
            return node.label

        # Other columns are per-source values; show values only for leaves.
        if isinstance(node, LeafNode):
            src_idx = column - 1
            if 0 <= src_idx < len(self.manager.sources):
                crt_obj = self._value_for_source(node, src_idx)
                if crt_obj is None or not crt_obj.exists:
                    return ""
                return "" if crt_obj.value is None else str(crt_obj.value)
        return ""

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = DISPLAY_ROLE,
    ) -> Any:
        if orientation != HORIZONTAL or role != DISPLAY_ROLE:
            return None
        if section == 0:
            return "Field"
        if self.merge_enabled and section == self._method_column():
            return "Method"
        if self.merge_enabled and section == self._result_column():
            return "Result"
        src_idx = section - 1
        if 0 <= src_idx < self.num_sources:
            adapter = self.manager.sources[src_idx]
            # Prefer explicit `name` attribute if defined, else class name.
            name = getattr(adapter, "name", adapter.__class__.__name__)
            return name
        return ""

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        base = QAbstractItemModel.flags(self, index)
        if not self.merge_enabled or not index.isValid():
            return base
        node = self._node_from_index(index)
        if not isinstance(node, LeafNode):
            return base
        col = index.column()
        if col == self._method_column() or col == self._result_column():
            return base | Qt.ItemFlags(ITEM_IS_EDITABLE)
        return base

    def setData(
        self,
        index: QModelIndex,
        value: Any,
        role: int = EDIT_ROLE,
    ) -> bool:
        if not index.isValid() or role != EDIT_ROLE:
            return False
        if not self.merge_enabled:
            return False
        node = self._node_from_index(index)
        if not isinstance(node, LeafNode):
            return False
        state = self._ensure_merge_state(node)
        col = index.column()
        if col == self._method_column():
            if not isinstance(value, str):
                return False
            state.selected_method = value
            state.resolved_value = None
            self.dataChanged.emit(index, index, [role])
            result_idx = self.index(
                index.row(), self._result_column(), index.parent()
            )
            self.dataChanged.emit(result_idx, result_idx, [role])
            return True
        if col == self._result_column():
            state.manual_value = value
            state.selected_method = MERGE_METHOD_MANUAL
            state.resolved_value = value
            self.dataChanged.emit(index, index, [role])
            method_idx = self.index(
                index.row(), self._method_column(), index.parent()
            )
            self.dataChanged.emit(method_idx, method_idx, [role])
            return True
        return False

    # Internal helpers
    # --------------------------------------------------------------------- #
    def _node_from_index(self, index: QModelIndex) -> BaseNode:
        if index.isValid():
            node = index.internalPointer()
            if isinstance(node, BaseNode):
                return node
        return self.root

    def _child_at(self, node: BaseNode, row: int) -> Optional[BaseNode]:
        if not isinstance(node, ParentNode):
            return None
        if 0 <= row < len(node.children):
            return node.children[row]
        return None

    def _row_of_child(self, parent: ParentNode, child: BaseNode) -> int:
        try:
            return parent.children.index(child)
        except Exception:
            logger.error(
                "Failed to find row of child %s in parent %s",
                child,
                parent,
                exc_info=True,
            )
            return -1

    # Note: merged tree building is performed by ComparatorManager.compare().

    # Formatting helpers
    # --------------------------------------------------------------------- #
    def _leaf_match_status(self, node: LeafNode) -> str:
        """Return 'equal', 'partial', or 'mismatch' for a leaf node."""
        base = self._value_for_source(node, 0)
        base_text = "" if base is None or not base.exists else str(base.value)
        all_equal = True
        has_partial = False
        for s_i in range(1, self.num_sources):
            crt = self._value_for_source(node, s_i)
            if crt is None or not crt.exists:
                all_equal = False
                continue
            crt_text = "" if crt.value is None else str(crt.value)
            if crt_text != base_text:
                all_equal = False
                if node.is_similar_enough(base_text, crt_text):
                    has_partial = True
        if all_equal:
            return "equal"
        return "partial" if has_partial else "mismatch"

    def _value_for_source(
        self, node: LeafNode, src_idx: int
    ) -> Optional[Value]:
        if 0 <= src_idx < len(node.values):
            v_obj = node.values[src_idx]
            if isinstance(v_obj, Value):
                return v_obj
        if 0 <= src_idx < len(self.manager.sources):
            src = self.manager.sources[src_idx]
            for v_obj in node.values:
                if (
                    isinstance(v_obj, Value)
                    and getattr(v_obj, "source", None) == src
                ):
                    return v_obj
        return None
