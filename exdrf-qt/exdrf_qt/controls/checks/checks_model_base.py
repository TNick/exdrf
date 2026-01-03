"""Common model utilities for check selection UIs.

This module provides a small hierarchy-enabled model base class implemented on
top of ``QAbstractTableModel`` so it can be used directly with ``QTreeView``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import (
    TYPE_CHECKING,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Set,
    cast,
)

from PyQt5.QtCore import QAbstractItemModel, QModelIndex, Qt, QVariant
from PyQt5.QtGui import QIcon

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from exdrf_util.check import Check

    from exdrf_qt.context import QtContext

logger = logging.getLogger(__name__)


class ChecksViewMode(StrEnum):
    """The view mode for checks models."""

    CATEGORY = "category"
    FLAT = "flat"


@dataclass(slots=True)
class CheckSearchOptions:
    """Options that control which check fields are searched when filtering.

    Attributes:
        search_id: Whether to search in the check id.
        search_title: Whether to search in the check title.
        search_description: Whether to search in the check description.
        search_tags: Whether to search in the check tags.
        search_category: Whether to search in the check category.
    """

    search_id: bool = True
    search_title: bool = True
    search_description: bool = True
    search_tags: bool = True
    search_category: bool = True


@dataclass(slots=True)
class _Node:
    """An internal node for the checks tree model.

    Attributes:
        kind: Either ``category`` or ``check``.
        title: The display title.
        description: The secondary description (may be empty).
        category: The category of the check or category node.
        check: The check instance for check nodes.
        parent: Parent node, if any.
        children: Child nodes.
    """

    kind: str
    title: str
    description: str = ""
    category: str = ""
    check: Optional["Check"] = None
    parent: Optional["_Node"] = None
    children: List["_Node"] = field(default_factory=list)


class ChecksTreeTableModelBase(QAbstractItemModel, QtUseContext):
    """A tree-capable model that still subclasses ``QAbstractTableModel``.

    This model uses one column and provides a node hierarchy suitable for
    displaying either a flat list or a category->check tree in a ``QTreeView``.

    Roles:
        - DisplayRole/EditRole: node title
        - DecorationRole: a generic icon
        - UserRole+1: node description
        - UserRole+2: the underlying check instance (or None)
        - UserRole+3: bool, whether the node is a category node
        - UserRole+4: check id (or empty string)

    Attributes:
        _view_mode: Current view mode.
        _sort_order: Current sort order for title sorting.
        _root: Root node.
        _check_icon: Icon for check nodes.
        _category_icon: Icon for category nodes.
    """

    _view_mode: ChecksViewMode
    _sort_order: Qt.SortOrder
    _root: _Node
    _check_icon: QIcon
    _category_icon: QIcon

    def __init__(self, ctx: "QtContext", parent=None) -> None:
        super().__init__(parent)
        self.ctx = ctx

        # Configure basic persistent state.
        self._view_mode = ChecksViewMode.CATEGORY
        self._sort_order = Qt.SortOrder.AscendingOrder
        self._root = _Node(kind="root", title="", parent=None)

        # Create generic icons using the current style.
        self._check_icon = self.get_icon("blueprint")
        self._category_icon = self.get_icon("folder")

    # ------------------------------------------------------------------
    # Public configuration API
    # ------------------------------------------------------------------

    def set_view_mode(self, mode: ChecksViewMode) -> None:
        """Set the view mode and rebuild the tree.

        Args:
            mode: The view mode to switch to.
        """
        if mode == self._view_mode:
            return

        self.beginResetModel()
        self._view_mode = mode
        self._rebuild_tree()
        self.endResetModel()

    def get_view_mode(self) -> ChecksViewMode:
        """Get the current view mode."""
        return self._view_mode

    def sort(
        self,
        column: int,
        order: Qt.SortOrder = Qt.SortOrder.AscendingOrder,
    ) -> None:  # noqa: N802
        """Sort by title (single-column model).

        Args:
            column: Column index (ignored, single column).
            order: Sort order.
        """
        del column
        if order == self._sort_order:
            return

        self.beginResetModel()
        self._sort_order = order
        self._rebuild_tree()
        self.endResetModel()

    # ------------------------------------------------------------------
    # Tree building hooks for subclasses
    # ------------------------------------------------------------------

    def _iter_checks(self) -> Iterable["Check"]:
        """Iterate through the checks that should appear in the model."""
        raise NotImplementedError

    def _rebuild_tree(self) -> None:
        """Rebuild the tree nodes from current state."""
        self._root.children.clear()

        # Collect and sort checks for stable UI ordering.
        checks = list(self._iter_checks())

        def check_title_key(chk: "Check") -> str:
            title = chk.title.strip() if chk.title else ""
            return (title if title else chk.check_id).lower()

        reverse = self._sort_order == Qt.SortOrder.DescendingOrder

        if self._view_mode == ChecksViewMode.FLAT:
            for chk in sorted(checks, key=check_title_key, reverse=reverse):
                self._root.children.append(self._mk_check_node(chk, self._root))
            return

        # Group by category, then sort categories and checks within them.
        grouped: Dict[str, List["Check"]] = {}
        for chk in checks:
            category = chk.category if chk.category else ""
            grouped.setdefault(category, []).append(chk)

        sorted_categories = sorted(
            grouped.keys(),
            key=lambda c: c.lower(),
            reverse=reverse,
        )
        for category in sorted_categories:
            cat_node = _Node(kind="category", title=category or "(no category)")
            cat_node.parent = self._root

            for chk in sorted(
                grouped[category],
                key=check_title_key,
                reverse=reverse,
            ):
                cat_node.children.append(self._mk_check_node(chk, cat_node))

            self._root.children.append(cat_node)

    def _mk_check_node(self, chk: "Check", parent: _Node) -> _Node:
        """Create a check node for the tree.

        Args:
            chk: Check instance.
            parent: Parent node.

        Returns:
            The created node.
        """
        title = chk.title.strip() if chk.title else ""
        if not title:
            title = chk.check_id
        node = _Node(
            kind="check",
            title=title,
            description=chk.description or "",
            category=chk.category or "",
            check=chk,
            parent=parent,
        )
        return node

    # ------------------------------------------------------------------
    # Helper API for controller code
    # ------------------------------------------------------------------

    def checks_from_indexes(
        self, indexes: Sequence[QModelIndex]
    ) -> List["Check"]:
        """Collect checks represented by the provided indexes.

        If a category node is selected, all checks under that category are
        returned.

        Args:
            indexes: Model indexes.

        Returns:
            List of check instances (deduplicated, stable).
        """
        seen_ids: Set[str] = set()
        result: List["Check"] = []

        # Normalize to column 0 indexes.
        col0 = [idx.sibling(idx.row(), 0) for idx in indexes if idx.isValid()]
        for idx in col0:
            node = self._node_for_index(idx)
            if node is None:
                continue
            if node.kind == "check" and node.check is not None:
                chk = node.check
                if chk.check_id not in seen_ids:
                    seen_ids.add(chk.check_id)
                    result.append(chk)
            elif node.kind == "category":
                for child in node.children:
                    if child.check is None:
                        continue
                    chk = child.check
                    if chk.check_id not in seen_ids:
                        seen_ids.add(chk.check_id)
                        result.append(chk)

        return result

    # ------------------------------------------------------------------
    # QAbstractItemModel API (tree-enabled)
    # ------------------------------------------------------------------

    def columnCount(
        self, parent: QModelIndex = QModelIndex()
    ) -> int:  # noqa: N802
        del parent
        return 1

    def rowCount(
        self, parent: QModelIndex = QModelIndex()
    ) -> int:  # noqa: N802
        node = self._node_for_index(parent)
        if node is None:
            node = self._root
        return len(node.children)

    def index(  # noqa: N802
        self,
        row: int,
        column: int,
        parent: QModelIndex = QModelIndex(),
    ) -> QModelIndex:
        if row < 0:
            return QModelIndex()
        if column < 0 or column >= self.columnCount(parent):
            return QModelIndex()

        parent_node = self._node_for_index(parent)
        if parent_node is None:
            parent_node = self._root

        if row >= len(parent_node.children):
            return QModelIndex()

        node = parent_node.children[row]
        return self.createIndex(row, column, node)

    def parent(self, child: QModelIndex) -> QModelIndex:  # type: ignore
        node = self._node_for_index(child)
        if node is None or node.parent is None or node.parent is self._root:
            return QModelIndex()

        parent_node = node.parent
        assert parent_node.parent is not None
        row = parent_node.parent.children.index(parent_node)
        return self.createIndex(row, 0, parent_node)

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:  # noqa: N802
        if not index.isValid():
            return cast(Qt.ItemFlags, Qt.ItemFlag.NoItemFlags)

        node = self._node_for_index(index)
        if node is None:
            return cast(Qt.ItemFlags, Qt.ItemFlag.NoItemFlags)

        # Categories are selectable too (for "add/remove all in category").
        return cast(
            Qt.ItemFlags,
            Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled,
        )

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return QVariant()

        node = self._node_for_index(index)
        if node is None:
            return QVariant()

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if index.column() == 0:
                return node.title
            return QVariant()

        if role == Qt.ItemDataRole.DecorationRole:
            if index.column() != 0:
                return QVariant()
            if node.kind == "category":
                return self._category_icon
            if node.kind == "check":
                return self._check_icon
            return QVariant()

        if role == Qt.ItemDataRole.ToolTipRole:
            if node.kind == "category":
                return node.title
            if node.description:
                return f"{node.title}\n\n{node.description}"
            return node.title

        if role == Qt.ItemDataRole.UserRole + 1:
            return node.description

        if role == Qt.ItemDataRole.UserRole + 2:
            return node.check

        if role == Qt.ItemDataRole.UserRole + 3:
            return node.kind == "category"

        if role == Qt.ItemDataRole.UserRole + 4:
            return node.check.check_id if node.check is not None else ""

        return QVariant()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _node_for_index(self, index: QModelIndex) -> Optional[_Node]:
        if not index.isValid():
            return None
        ptr = index.internalPointer()
        if isinstance(ptr, _Node):
            return ptr
        return None
