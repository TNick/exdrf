from __future__ import annotations

import logging
from difflib import SequenceMatcher
from typing import Any, Optional

from PyQt5.QtCore import QAbstractItemModel, QModelIndex, Qt
from PyQt5.QtGui import QBrush, QColor

from exdrf_qt.comparator.logic.manager import ComparatorManager
from exdrf_qt.comparator.logic.nodes import (
    BaseNode,
    LeafNode,
    ParentNode,
    Value,
)

logger = logging.getLogger(__name__)

# Constants to avoid enum attribute typing issues in some stub versions.
DISPLAY_ROLE = int(getattr(Qt, "DisplayRole", 0))
EDIT_ROLE = int(getattr(Qt, "EditRole", 2))
BACKGROUND_ROLE = int(getattr(Qt, "BackgroundRole", 8))
HORIZONTAL = int(getattr(Qt, "Horizontal", 1))
NO_ITEM_FLAGS = int(getattr(Qt, "NoItemFlags", 0))
ITEM_IS_ENABLED = int(getattr(Qt, "ItemIsEnabled", 1))
ITEM_IS_SELECTABLE = int(getattr(Qt, "ItemIsSelectable", 1 << 1))
HTML_ROLE = int(getattr(Qt, "UserRole", 0)) + 1


class ComparatorTreeModel(QAbstractItemModel):
    """Qt item model that exposes comparator data as a tree.

    The model merges the per-source trees provided by the manager into a single
    combined tree keyed by each node's `key` (falling back to the `label`
    when the key is empty). The model shows 1 + N columns, where the first
    column contains the node label and the next N columns contain values for
    each source (only leaf nodes have values; non-leaf nodes show empty cells).

    Attributes:
        manager: The comparator manager providing the sources and data.
        root: The combined root node used by the model.
        num_sources: Number of sources provided by the manager.
    """

    def __init__(
        self, manager: ComparatorManager, parent: Optional[Any] = None
    ) -> None:
        super().__init__(parent)

        # Store manager and number of sources.
        self.manager: ComparatorManager = manager
        self.num_sources: int = len(self.manager.sources)

        # Use unified tree already built into manager.root by compare().
        self.root: ParentNode = self.manager.root

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
        # One label column + one column per source.
        return 1 + self.num_sources

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
                    if crt_text != base_text and self._is_similar_enough(
                        base_text, crt_text
                    ):
                        left_html, _ = self._html_diff(base_text, crt_text)
                        return left_html
                return None

            if column > 0:
                src_idx = column - 1
                crt_obj = self._value_for_source(node, src_idx)
                if crt_obj is None or not crt_obj.exists or crt_obj is base_obj:
                    return None
                crt_text = "" if crt_obj.value is None else str(crt_obj.value)
                if self._is_similar_enough(base_text, crt_text):
                    _, right_html = self._html_diff(base_text, crt_text)
                    return right_html
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
        src_idx = section - 1
        if 0 <= src_idx < self.num_sources:
            adapter = self.manager.sources[src_idx]
            # Prefer explicit `name` attribute if defined, else class name.
            name = getattr(adapter, "name", adapter.__class__.__name__)
            return name
        return ""

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        return QAbstractItemModel.flags(self, index)

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
                if self._is_similar_enough(base_text, crt_text):
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

    def _is_similar_enough(self, a: str, b: str) -> bool:
        try:
            return SequenceMatcher(None, a, b).ratio() >= 0.6
        except Exception:
            logger.error(
                "Failed to compare %s and %s",
                a,
                b,
                exc_info=True,
            )
            return False

    def _html_escape(self, s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _html_diff(self, left: str, right: str) -> tuple[str, str]:
        sm = SequenceMatcher(None, left, right)

        def wrap_ins(text: str) -> str:
            if not text:
                return ""
            return '<span style="background:#e6e6e6;">' + text + "</span>"

        def wrap_del(text: str) -> str:
            if not text:
                return ""
            return (
                '<span style="background:#e6e6e6;'
                'text-decoration:line-through;">' + text + "</span>"
            )

        l_parts: list[str] = []
        r_parts: list[str] = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            l_seg = self._html_escape(left[i1:i2])
            r_seg = self._html_escape(right[j1:j2])
            if tag == "equal":
                l_parts.append(l_seg)
                r_parts.append(r_seg)
            elif tag == "replace":
                l_parts.append(wrap_del(l_seg))
                r_parts.append(wrap_ins(r_seg))
            elif tag == "delete":
                l_parts.append(wrap_del(l_seg))
            elif tag == "insert":
                r_parts.append(wrap_ins(r_seg))

        return ("".join(l_parts), "".join(r_parts))
