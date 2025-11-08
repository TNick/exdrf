from __future__ import annotations

import logging
from typing import Any, Optional

from PyQt5.QtCore import QAbstractItemModel, QModelIndex, Qt

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
HORIZONTAL = int(getattr(Qt, "Horizontal", 1))
NO_ITEM_FLAGS = int(getattr(Qt, "NoItemFlags", 0))
ITEM_IS_ENABLED = int(getattr(Qt, "ItemIsEnabled", 1))
ITEM_IS_SELECTABLE = int(getattr(Qt, "ItemIsSelectable", 1 << 1))


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
        return node.child_count if isinstance(node, ParentNode) else 0

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        # One label column + one column per source.
        return 1 + self.num_sources

    def data(self, index: QModelIndex, role: int = DISPLAY_ROLE) -> Any:
        if not index.isValid() or role not in (DISPLAY_ROLE, EDIT_ROLE):
            return None

        node: BaseNode = self._node_from_index(index)
        column = index.column()

        # First column is the node label.
        if column == 0:
            return node.label

        # Other columns are per-source values; show values only for leaves.
        if isinstance(node, LeafNode):
            src_idx = column - 1
            if 0 <= src_idx < len(self.manager.sources):
                # Prefer aligned-by-index; else locate by source.
                if 0 <= src_idx < len(node.values):
                    v_obj = node.values[src_idx]
                    if isinstance(v_obj, Value):
                        if not v_obj.exists:
                            return ""
                        return "" if v_obj.value is None else v_obj.value
                src = self.manager.sources[src_idx]
                for v_obj in node.values:
                    if (
                        isinstance(v_obj, Value)
                        and getattr(v_obj, "source", None) == src
                    ):
                        if not v_obj.exists:
                            return ""
                        return "" if v_obj.value is None else v_obj.value
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
            return -1

    # Note: merged tree building is performed by ComparatorManager.compare().
