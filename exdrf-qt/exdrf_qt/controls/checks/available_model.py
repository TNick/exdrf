"""Qt model for available checks."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, Iterable, List, Set

from PyQt5.QtCore import Qt

from exdrf_qt.controls.checks.checks_model_base import (
    CheckSearchOptions,
    ChecksTreeTableModelBase,
    ChecksViewMode,
)

if TYPE_CHECKING:
    from exdrf_util.check import Check

    from exdrf_qt.context import QtContext

logger = logging.getLogger(__name__)


class AvailableChecksModel(ChecksTreeTableModelBase):
    """Model for available checks with filtering, sorting, and view modes.

    Checks are discovered via ``exdrf_util.check.get_all_checks`` and kept as
    instances so they can be moved to the selected model without recreating
    them.

    Attributes:
        _all_checks: The discovered checks (instances).
        _checks_by_id: Mapping of check id to the kept check instance.
        _excluded_ids: Set of check ids that should be hidden (selected checks).
        _filter_text: The current filter text.
        _search_options: Which fields are searched.
    """

    _all_checks: List["Check"]
    _checks_by_id: Dict[str, "Check"]
    _excluded_ids: Set[str]
    _filter_text: str
    _search_options: CheckSearchOptions

    def __init__(self, ctx: "QtContext", parent=None) -> None:
        super().__init__(ctx, parent=parent)

        # Configure state for discovery/filtering.
        self._all_checks = []
        self._checks_by_id = {}
        self._excluded_ids = set()
        self._filter_text = ""
        self._search_options = CheckSearchOptions()

        # Discover initial checks.
        self.reload_checks()

    def reload_checks(self) -> None:
        """Reload checks from the plugin registry."""
        from exdrf_util.check import get_all_checks

        self.beginResetModel()

        # Keep check instances stable across reloads based on check_id.
        discovered = get_all_checks(ctx=self.ctx, for_gui=True)
        new_by_id: Dict[str, "Check"] = {}
        new_list: List["Check"] = []
        for chk in discovered:
            kept = self._checks_by_id.get(chk.check_id, chk)
            new_by_id[chk.check_id] = kept
            new_list.append(kept)

        self._checks_by_id = new_by_id
        self._all_checks = new_list

        # Rebuild the tree with the current filter/mode/sort settings.
        self._rebuild_tree()

        self.endResetModel()

    def set_view_mode(self, mode: ChecksViewMode) -> None:
        """Set the view mode and rebuild."""
        super().set_view_mode(mode)

    def set_filter_text(self, text: str) -> None:
        """Set filter text and rebuild the view.

        Args:
            text: Filter substring. Empty string disables filtering.
        """
        text = text or ""
        if text == self._filter_text:
            return

        self.beginResetModel()
        self._filter_text = text
        self._rebuild_tree()
        self.endResetModel()

    def set_search_options(self, options: CheckSearchOptions) -> None:
        """Set the search options used when filtering.

        Args:
            options: Search options.
        """
        if options == self._search_options:
            return

        self.beginResetModel()
        self._search_options = options
        self._rebuild_tree()
        self.endResetModel()

    def set_excluded_check_ids(self, ids: Set[str]) -> None:
        """Exclude checks from the available list.

        Args:
            ids: Check ids to exclude.
        """
        if ids == self._excluded_ids:
            return

        self.beginResetModel()
        self._excluded_ids = set(ids)
        self._rebuild_tree()
        self.endResetModel()

    def take_checks_by_id(self, ids: Set[str]) -> List["Check"]:
        """Take checks out of this model by id.

        This marks the ids as excluded and returns the corresponding check
        instances (if present).

        Args:
            ids: Check ids to take.

        Returns:
            List of check instances.
        """
        taken: List["Check"] = []
        for chk in self._all_checks:
            if chk.check_id in ids:
                taken.append(chk)

        if not taken:
            return []

        # Exclude them from this model and rebuild.
        self.set_excluded_check_ids(self._excluded_ids | ids)
        return taken

    def put_back_checks(self, checks: Iterable["Check"]) -> None:
        """Make the given checks available again.

        Args:
            checks: Checks to un-exclude.
        """
        ids = {chk.check_id for chk in checks}
        if not ids:
            return

        new_excluded = set(self._excluded_ids)
        new_excluded.difference_update(ids)
        self.set_excluded_check_ids(new_excluded)

    # ------------------------------------------------------------------
    # Base hooks
    # ------------------------------------------------------------------

    def _iter_checks(self) -> Iterable["Check"]:
        # Apply exclusion first.
        checks = [
            chk
            for chk in self._all_checks
            if chk.check_id not in self._excluded_ids
        ]

        # Apply filtering.
        if not self._filter_text.strip():
            return checks

        needle = self._filter_text.strip().lower()

        def matches(chk: "Check") -> bool:
            if (
                self._search_options.search_id
                and needle in chk.check_id.lower()
            ):
                return True
            if (
                self._search_options.search_title
                and needle in (chk.title or "").lower()
            ):
                return True
            if (
                self._search_options.search_description
                and needle in (chk.description or "").lower()
            ):
                return True
            if (
                self._search_options.search_category
                and needle in (chk.category or "").lower()
            ):
                return True
            if self._search_options.search_tags:
                for tag in chk.tags or []:
                    if needle in tag.lower():
                        return True
            return False

        return [chk for chk in checks if matches(chk)]

    def sort(
        self,
        column: int,
        order: Qt.SortOrder = Qt.SortOrder.AscendingOrder,
    ) -> None:  # noqa: N802
        super().sort(column, order)
