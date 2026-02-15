"""Per-column substring filter proxy with numeric-aware sorting."""

import logging
from typing import Dict

from PyQt5.QtCore import QModelIndex, QSortFilterProxyModel, Qt

logger = logging.getLogger(__name__)
VERBOSE = 10


class ColumnFilterProxy(QSortFilterProxyModel):
    """Proxy model that applies per-column substring filters (case-insensitive).

    Attributes:
        _filters: Map from column index to current filter text.
    """

    # Private attributes
    _filters: Dict[int, str]

    def __init__(self) -> None:
        """Initialize the proxy model and filtering behavior."""
        super().__init__()
        self._filters = {}
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setDynamicSortFilter(True)

    def set_filter(self, column: int, text: str) -> None:
        """Set a filter string for a given column.

        Args:
            column: Column index.
            text: Substring to match (case-insensitive).
        """
        logger.log(
            VERBOSE,
            "ColumnFilterProxy: set_filter col=%d text=%r",
            column,
            text,
        )
        self._filters[column] = text or ""
        self.invalidateFilter()

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        """Forward header data from the source model so the header shows labels.

        Args:
            section: Section index.
            orientation: Horizontal or Vertical.
            role: Qt role (Display role is used for labels).

        Returns:
            Header label from source model, or None.
        """
        src = self.sourceModel()
        if src is not None:
            return src.headerData(section, orientation, role)
        return None

    def filterAcceptsRow(
        self, source_row: int, source_parent: QModelIndex
    ) -> bool:  # noqa: N802
        """Decide whether a source row matches all active column filters.

        Args:
            source_row: Source model row.
            source_parent: Source parent index.

        Returns:
            True if row matches all filters; False otherwise.
        """
        model = self.sourceModel()
        if model is None:
            return True
        for col, pattern in self._filters.items():
            if not pattern:
                continue
            idx = model.index(source_row, col, source_parent)
            text = str(model.data(idx, Qt.ItemDataRole.DisplayRole) or "")
            if pattern.lower() not in text.lower():
                return False
        return True

    def lessThan(
        self, left: QModelIndex, right: QModelIndex
    ) -> bool:  # type: ignore[override]
        """Sort numbers numerically when possible, fallback to text compare.

        Args:
            left: Left index in source model.
            right: Right index in source model.

        Returns:
            True if left < right according to numeric-aware ordering.
        """
        model = self.sourceModel()
        if model is None:
            return super().lessThan(left, right)

        lv = model.data(left, Qt.ItemDataRole.DisplayRole)
        rv = model.data(right, Qt.ItemDataRole.DisplayRole)

        def _to_num(val):
            if val is None:
                return None
            s = str(val).strip()
            if not s:
                return None
            try:
                # Try integer first for stable ordering
                return int(s)
            except Exception:
                try:
                    return float(s)
                except Exception:
                    return None

        ln = _to_num(lv)
        rn = _to_num(rv)

        if ln is not None and rn is not None:
            return ln < rn

        # Fallback: case-insensitive text compare
        ls = ("" if lv is None else str(lv)).lower()
        rs = ("" if rv is None else str(rv)).lower()
        return ls < rs
