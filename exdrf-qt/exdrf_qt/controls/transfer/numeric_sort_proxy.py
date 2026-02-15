"""Sort/filter proxy for numeric-aware table column sorting."""

import logging
from typing import Dict

from PyQt5.QtCore import QModelIndex, QSortFilterProxyModel, Qt

logger = logging.getLogger(__name__)
VERBOSE = 1


class NumericSortProxy(QSortFilterProxyModel):
    """Proxy that sorts numbers numerically when possible.

    Falls back to case-insensitive text sort when values are not numeric.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._filters: Dict[int, str] = {}
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setDynamicSortFilter(True)

    def set_filter(self, column: int, text: str) -> None:
        """Set filter text for a column."""
        self._filters[column] = text or ""
        self.invalidateFilter()

    def filterAcceptsRow(
        self, source_row: int, source_parent: QModelIndex
    ) -> bool:  # noqa: N802
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

    # type: ignore[override]
    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
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
                return int(s)
            except Exception:
                try:
                    return float(s)
                except Exception as e:
                    logger.log(VERBOSE, "Non-numeric sort value %r: %s", val, e)
                    return None

        ln = _to_num(lv)
        rn = _to_num(rv)
        if ln is not None and rn is not None:
            return ln < rn
        ls = ("" if lv is None else str(lv)).lower()
        rs = ("" if rv is None else str(rv)).lower()
        return ls < rs
