"""Qt model for displaying check results.

The results can be displayed as:
- grouped: category -> check -> result
- flat: result rows with an extra column containing the check title
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    cast,
)

from PyQt5.QtCore import QAbstractItemModel, QModelIndex, Qt, QVariant
from PyQt5.QtGui import QIcon

from exdrf_qt.context import QtContext
from exdrf_qt.context_use import QtUseContext

logger = logging.getLogger(__name__)


class ResultsViewMode(StrEnum):
    """View mode for results."""

    GROUPED = "grouped"
    FLAT = "flat"


@dataclass(slots=True)
class ResultEntry:
    """A single result entry.

    Attributes:
        check_id: Check id.
        check_title: Check title.
        check_description: Check description.
        check_category: Check category.
        params_values: Current parameter values used for this run.
        result: The result of the check (serialized dict).
        description: Cached, UI-translated description for this result.
    """

    check_id: str
    check_title: str
    check_description: str
    check_category: str
    params_values: Dict[str, Any]
    result: Dict[str, Any]
    description: str


@dataclass(slots=True)
class _Node:
    """Internal node for the results model."""

    kind: str
    title: str = ""
    entry: Optional[ResultEntry] = None
    parent: Optional["_Node"] = None
    children: List["_Node"] = field(default_factory=list)


class ResultsModel(QAbstractItemModel, QtUseContext):
    """Model for displaying check results with filtering and sorting."""

    ctx: "QtContext"

    _view_mode: ResultsViewMode
    _filter_text: str
    _hidden_states: Set[str]
    _sort_column: int
    _sort_order: Qt.SortOrder

    _entries: List[ResultEntry]
    _root: _Node

    def __init__(self, ctx: "QtContext", parent=None) -> None:
        super().__init__(parent)
        self.ctx = ctx

        self._view_mode = ResultsViewMode.GROUPED
        self._filter_text = ""
        self._hidden_states = set()
        self._sort_column = 0
        self._sort_order = Qt.SortOrder.AscendingOrder

        self._entries = []
        self._root = _Node(kind="root")

        self._rebuild_tree()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Clear all results."""
        self.beginResetModel()
        self._entries = []
        self._rebuild_tree()
        self.endResetModel()

    def set_view_mode(self, mode: ResultsViewMode) -> None:
        """Set the view mode."""
        if mode == self._view_mode:
            return
        self.beginResetModel()
        self._view_mode = mode
        self._rebuild_tree()
        self.endResetModel()

    def get_view_mode(self) -> ResultsViewMode:
        """Get current view mode."""
        return self._view_mode

    def set_filter_text(self, text: str) -> None:
        """Set filter text."""
        text = text or ""
        if text == self._filter_text:
            return
        self.beginResetModel()
        self._filter_text = text
        self._rebuild_tree()
        self.endResetModel()

    def set_hidden_states(self, states: Set[str]) -> None:
        """Set which result states should be hidden.

        Args:
            states: Set of result state strings to hide.
        """
        states = set(states or set())
        if states == self._hidden_states:
            return
        self.beginResetModel()
        self._hidden_states = states
        self._rebuild_tree()
        self.endResetModel()

    def get_hidden_states(self) -> Set[str]:
        """Get currently hidden result states."""
        return set(self._hidden_states)

    def get_present_states(self) -> Set[str]:
        """Get states present in the currently loaded results."""
        states: Set[str] = set()
        for e in self._entries:
            states.add(self._entry_state(e))
        return states

    def add_results(
        self,
        *,
        check_id: str,
        check_title: str,
        check_description: str,
        check_category: str,
        params_values: Dict[str, Any],
        results: Iterable[Dict[str, Any]],
    ) -> None:
        """Add results for a check.

        Args:
            check_id: Check id.
            check_title: Check title.
            check_description: Check description.
            check_category: Check category.
            params_values: Parameter values.
            results: Results to add.
        """

        # Precompute UI-facing result description once (avoids repeated
        # translations in sort/filter/paint, and only falls back to the
        # worker-provided description if we cannot translate in the GUI).
        new = [
            ResultEntry(
                check_id=check_id,
                check_title=check_title,
                check_description=check_description,
                check_category=check_category,
                params_values=dict(params_values),
                result=dict(r),
                description=self._compute_result_description(r),
            )
            for r in results
        ]
        if not new:
            return

        self.beginResetModel()
        self._entries.extend(new)
        self._rebuild_tree()
        self.endResetModel()

    def sort(
        self,
        column: int,
        order: Qt.SortOrder = Qt.SortOrder.AscendingOrder,
    ) -> None:  # noqa: N802
        """Sort results."""
        if column == self._sort_column and order == self._sort_order:
            return
        self.beginResetModel()
        self._sort_column = column
        self._sort_order = order
        self._rebuild_tree()
        self.endResetModel()

    def get_entry_for_index(self, index: QModelIndex) -> Optional[ResultEntry]:
        """Get result entry for an index (only valid on result nodes)."""
        node = self._node_for_index(index)
        if node is None:
            return None
        return node.entry

    # ------------------------------------------------------------------
    # QAbstractItemModel
    # ------------------------------------------------------------------

    def columnCount(
        self, parent: QModelIndex = QModelIndex()
    ) -> int:  # noqa: N802
        del parent
        if self._view_mode == ResultsViewMode.FLAT:
            return 2
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
            return Qt.ItemFlags(Qt.ItemFlag.NoItemFlags)
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

        if role == Qt.ItemDataRole.ToolTipRole:
            if node.kind == "result" and node.entry is not None:
                return node.entry.description
            return QVariant()

        if role == Qt.ItemDataRole.DecorationRole and index.column() == 0:
            if node.kind == "result" and node.entry is not None:
                return self._icon_for_state(
                    str(node.entry.result.get("state", "failed") or "failed")
                )
            if node.kind == "category":
                return self.get_icon("folder")
            if node.kind == "check":
                return self.get_icon("blueprint")
            return QVariant()

        if role not in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return QVariant()

        if self._view_mode == ResultsViewMode.FLAT:
            assert node.kind == "result"
            assert node.entry is not None
            if index.column() == 0:
                return node.entry.description
            if index.column() == 1:
                return node.entry.check_title
            return QVariant()

        # Grouped view: single column with node title.
        if index.column() != 0:
            return QVariant()
        return node.title

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

    def _entry_state(self, entry: ResultEntry) -> str:
        """Extract the state string from a result entry."""
        return str(entry.result.get("state", "failed") or "failed")

    def _compute_result_description(self, result: Dict[str, Any]) -> str:
        """Compute the UI-facing description for a single result.

        Args:
            result: The serialized result dict from the check runner.

        Returns:
            The description to display in the GUI (already translated in the
            current GUI language).
        """
        t_key = str(result.get("t_key", "") or "")
        res_text = ""

        # Prefer translating in the GUI process (so language matches the UI).
        if t_key:
            res_text = self.ctx.t(
                t_key, "", **dict(result.get("params", {}) or {})
            )

        # Fall back to any description provided by the worker result.
        if not res_text:
            res_text = cast(str, result.get("description", None))

            # Final fallback.
            if not res_text:
                res_text = self.ctx.t("checks.result.unknown", "No description")

        return res_text

    def _icon_for_state(self, state: str) -> QIcon:
        name = {
            "passed": "tick",
            "skipped": "check_box_uncheck",
            "fixed": "tick_button",
            "partially_fixed": "tick_red",
            "not_fixed": "exclamation",
            "failed": "script_red",
        }.get(state, "blueprint")
        return self.get_icon(name)

    def _matches_filter(self, entry: ResultEntry) -> bool:
        if not self._filter_text.strip():
            return True

        needle = self._filter_text.strip().lower()
        hay = " ".join(
            [
                entry.check_id,
                entry.check_title,
                entry.check_category,
                entry.description,
            ]
        ).lower()
        return needle in hay

    def _rebuild_tree(self) -> None:
        self._root.children = []

        # Filter by text.
        entries = [e for e in self._entries if self._matches_filter(e)]

        # Filter by state.
        if self._hidden_states:
            entries = [
                e
                for e in entries
                if self._entry_state(e) not in self._hidden_states
            ]

        # Sort.
        reverse = self._sort_order == Qt.SortOrder.DescendingOrder

        def key_for_entry(e: ResultEntry) -> Tuple[str, str]:
            if self._sort_column == 1:
                return (
                    e.check_title.lower(),
                    e.description.lower(),
                )
            return (e.description.lower(), e.check_title.lower())

        entries = sorted(entries, key=key_for_entry, reverse=reverse)

        if self._view_mode == ResultsViewMode.FLAT:
            for e in entries:
                node = _Node(
                    kind="result",
                    title=e.description,
                    entry=e,
                    parent=self._root,
                )
                self._root.children.append(node)
            return

        # Grouped view: category -> check -> result.
        by_cat: Dict[str, Dict[str, List[ResultEntry]]] = {}
        for e in entries:
            category = e.check_category or "(no category)"
            by_cat.setdefault(category, {}).setdefault(e.check_id, []).append(e)

        for category in sorted(by_cat.keys(), key=lambda x: x.lower()):
            # Count total results in this category.
            cat_result_count = sum(len(v) for v in by_cat[category].values())
            cat_title = f"{category} ({cat_result_count})"
            cat_node = _Node(
                kind="category", title=cat_title, parent=self._root
            )
            self._root.children.append(cat_node)

            checks_map = by_cat[category]
            for check_id in sorted(checks_map.keys(), key=lambda x: x.lower()):
                first = checks_map[check_id][0]
                result_count = len(checks_map[check_id])
                check_title = (
                    f"{first.check_title or check_id} ({result_count})"
                )
                check_node = _Node(
                    kind="check",
                    title=check_title,
                    parent=cat_node,
                )
                cat_node.children.append(check_node)

                for e in checks_map[check_id]:
                    res_node = _Node(
                        kind="result",
                        title=e.description,
                        entry=e,
                        parent=check_node,
                    )
                    check_node.children.append(res_node)
