"""Qt model for selected checks."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Set, Tuple

from PyQt5.QtCore import QModelIndex, Qt, QVariant

from exdrf_qt.controls.checks.checks_model_base import (
    ChecksTreeTableModelBase,
    ChecksViewMode,
)

PROGRESS_ROLE = Qt.ItemDataRole.UserRole + 10

if TYPE_CHECKING:
    from exdrf_util.check import Check

    from exdrf_qt.context import QtContext

logger = logging.getLogger(__name__)


class SelectedChecksModel(ChecksTreeTableModelBase):
    """Model for selected checks (no filtering, supports view modes/sorting).

    Attributes:
        _checks: The selected checks (instances).
        _running: Whether tasks are currently running.
        _progress: Progress per check id in range [-1, 100].
    """

    _checks: List["Check"]
    _running: bool
    _progress: Dict[str, int]
    _indeterminate: Set[str]
    _failed: Set[str]

    def __init__(self, ctx: "QtContext", parent=None) -> None:
        super().__init__(ctx, parent=parent)

        # Configure selection state.
        self._checks = []
        self._running = False
        self._progress = {}
        self._indeterminate = set()
        self._failed = set()
        self._rebuild_tree()

    def set_view_mode(self, mode: ChecksViewMode) -> None:
        """Set the view mode and rebuild."""
        super().set_view_mode(mode)

    def set_running(self, running: bool) -> None:
        """Toggle running mode (adds/removes the progress column).

        Args:
            running: Whether checks are running.
        """
        if running == self._running:
            return

        self.beginResetModel()
        self._running = running
        if not running:
            self._progress = {}
            self._indeterminate = set()
            self._failed = set()
        self.endResetModel()

    def set_check_progress(
        self,
        check_id: str,
        progress: int,
        indeterminate: bool = False,
    ) -> None:
        """Update progress for a check.

        Args:
            check_id: Check id.
            progress: Progress in range [-1, 100].
            indeterminate: Whether the task is indeterminate.
        """
        if not check_id:
            return

        if indeterminate:
            self._indeterminate.add(check_id)
        else:
            self._indeterminate.discard(check_id)

        self._progress[check_id] = progress

        # Emit data changed for the progress column if possible.
        if not self._running:
            return

        idx = self._find_check_index(check_id)
        if idx is None:
            return

        left = idx.sibling(idx.row(), 1)
        right = idx.sibling(idx.row(), 1)
        self.dataChanged.emit(left, right)

    def set_check_failed(self, check_id: str) -> None:
        """Mark a check as failed.

        Args:
            check_id: Check id.
        """
        if not check_id:
            return

        self._failed.add(check_id)
        self._indeterminate.discard(check_id)
        self._progress[check_id] = 100

        if not self._running:
            return

        idx = self._find_check_index(check_id)
        if idx is None:
            return

        left = idx.sibling(idx.row(), 1)
        right = idx.sibling(idx.row(), 1)
        self.dataChanged.emit(left, right)

    def get_progress_snapshot(self) -> Tuple[Dict[str, int], Set[str]]:
        """Get progress snapshot for total progress computation.

        Returns:
            Tuple(progress_by_id, indeterminate_ids)
        """
        return dict(self._progress), set(self._indeterminate)

    def _find_check_index(self, check_id: str) -> Optional[QModelIndex]:
        """Find the QModelIndex for a check node (column 0)."""
        root = QModelIndex()
        for row in range(self.rowCount(root)):
            idx = self.index(row, 0, root)
            is_category = bool(idx.data(Qt.ItemDataRole.UserRole + 3))
            if is_category:
                for crow in range(self.rowCount(idx)):
                    c_idx = self.index(crow, 0, idx)
                    cid = str(c_idx.data(Qt.ItemDataRole.UserRole + 4) or "")
                    if cid == check_id:
                        return c_idx
            else:
                cid = str(idx.data(Qt.ItemDataRole.UserRole + 4) or "")
                if cid == check_id:
                    return idx
        return None

    # ------------------------------------------------------------------
    # QAbstractItemModel API
    # ------------------------------------------------------------------

    def columnCount(
        self, parent: QModelIndex = QModelIndex()
    ) -> int:  # noqa: N802
        del parent
        return 2 if self._running else 1

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return QVariant()

        node = self._node_for_index(index)
        if node is None:
            return QVariant()

        if index.column() == 0:
            return super().data(index, role)

        check_id = node.check.check_id if node.check is not None else ""
        is_category = node.kind == "category"

        # Align and expose structured payload for the delegate.
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter

        if role == PROGRESS_ROLE:
            return self._progress_payload(check_id, is_category)

        # Progress column.
        if role not in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return QVariant()

        if is_category or not check_id:
            return QVariant()

        return self._progress_text(check_id)

    def add_checks(self, checks: Iterable["Check"]) -> None:
        """Add checks to the selected list (deduplicated by id).

        Args:
            checks: Checks to add.
        """
        checks = list(checks)
        if not checks:
            return

        existing = {chk.check_id for chk in self._checks}
        added = [chk for chk in checks if chk.check_id not in existing]
        if not added:
            return

        self.beginResetModel()
        self._checks.extend(added)
        for chk in added:
            self._progress.setdefault(chk.check_id, -1)
        self._rebuild_tree()
        self.endResetModel()

    def remove_checks_by_id(self, ids: Set[str]) -> List["Check"]:
        """Remove checks by id.

        Args:
            ids: Check ids to remove.

        Returns:
            List of removed check instances.
        """
        if not ids:
            return []

        removed = [chk for chk in self._checks if chk.check_id in ids]
        if not removed:
            return []

        self.beginResetModel()
        self._checks = [chk for chk in self._checks if chk.check_id not in ids]
        for chk_id in ids:
            self._progress.pop(chk_id, None)
            self._indeterminate.discard(chk_id)
            self._failed.discard(chk_id)
        self._rebuild_tree()
        self.endResetModel()
        return removed

    def clear(self) -> None:
        """Clear all selected checks."""
        if not self._checks:
            return

        self.beginResetModel()
        self._checks = []
        self._progress = {}
        self._indeterminate = set()
        self._failed = set()
        self._rebuild_tree()
        self.endResetModel()

    def get_check_ids(self) -> Set[str]:
        """Get the selected check ids."""
        return {chk.check_id for chk in self._checks}

    def get_checks(self) -> List["Check"]:
        """Get selected check instances (stable order)."""
        return list(self._checks)

    def get_check(self, check_id: str) -> Optional["Check"]:
        """Get a check by id."""
        return next(
            (chk for chk in self._checks if chk.check_id == check_id), None
        )

    def _progress_text(self, check_id: str) -> str:
        """Format the progress text for the given check id.

        Args:
            check_id: Check identifier.

        Returns:
            Human-readable progress text.
        """
        if check_id in self._failed:
            return self.t("checks.progress.failed", "ERR")

        if check_id in self._indeterminate:
            return "…"

        progress = self._progress.get(check_id)
        if progress is None or progress < 0:
            return ""
        if progress > 100:
            progress = 100
        return f"{progress}%"

    def _progress_payload(self, check_id: str, is_category: bool) -> QVariant:
        """Build a payload with progress information for delegates.

        Args:
            check_id: Check identifier.
            is_category: Whether the row represents a category.

        Returns:
            QVariant containing a mapping with progress details.
        """
        if is_category or not check_id:
            return QVariant()

        progress = self._progress.get(check_id, -1)
        if progress is None:
            progress = -1

        if progress > 100:
            progress = 100

        payload = {
            "value": progress,
            "indeterminate": check_id in self._indeterminate,
            "failed": check_id in self._failed,
            "text": self._progress_text(check_id),
        }
        return QVariant(payload)

    # ------------------------------------------------------------------
    # Base hooks
    # ------------------------------------------------------------------

    def _iter_checks(self) -> Iterable["Check"]:
        return self._checks

    def sort(
        self,
        column: int,
        order: Qt.SortOrder = Qt.SortOrder.AscendingOrder,
    ) -> None:  # noqa: N802
        super().sort(column, order)
