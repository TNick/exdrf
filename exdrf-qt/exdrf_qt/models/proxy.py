"""Proxy models for advanced filtering.

This module provides a reusable multi-column filtering proxy model that supports
per-column text filters and an optional secondary predicate such as a content
search across the underlying record.
"""

import logging
from typing import Any, Callable, Dict, Optional

from PyQt5.QtCore import QModelIndex, QRegExp, QSortFilterProxyModel, Qt

SORT_ROLE = Qt.ItemDataRole.UserRole + 5

logger = logging.getLogger(__name__)


class ProxyModel(QSortFilterProxyModel):
    """A QSortFilterProxyModel that supports per-column filters.

    The model maintains a map of column index -> compiled regex. When deciding
    whether a row is accepted, all active column regexes must match the data in
    their respective columns. Optionally a ``row_predicate`` may be provided to
    include custom logic (e.g., full-text content search).

    Attributes:
        _column_filters: Map of column to compiled QRegExp.
        _row_predicate: Optional predicate receiving the source row index that
            can veto or accept a row after column filtering.
    """

    _column_filters: Dict[int, QRegExp]
    _row_predicate: Optional[
        Callable[[int, QModelIndex, Qt.CaseSensitivity], bool]
    ]
    _numeric_sort_extractors: Dict[int, Callable[[Any], str]]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._column_filters = {}
        self._row_predicate = None
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._numeric_sort_extractors = {}

    def setFilterCaseSensitivity(self, cs: Qt.CaseSensitivity) -> None:
        k_v = list(self._column_filters.items())
        self._column_filters.clear()
        for k, v in k_v:
            self._column_filters[k] = QRegExp(
                v.pattern(), cs, v.patternSyntax()
            )
        super().setFilterCaseSensitivity(cs)

    def set_column_filter(self, column: int, text: str) -> None:
        """Set or clear the filter for a given column.

        Args:
            column: The column index.
            text: The filter text; clears the filter if empty.
        """
        sensitivity = self.filterCaseSensitivity()

        if text:
            rx = QRegExp(
                text,
                sensitivity,
                QRegExp.PatternSyntax.RegExp,
            )
            self._column_filters[column] = rx
        else:
            self._column_filters.pop(column, None)
        self.invalidateFilter()

    def set_row_predicate(
        self,
        predicate: Optional[
            Callable[[int, QModelIndex, Qt.CaseSensitivity], bool]
        ],
    ) -> None:
        """Set the custom row predicate.

        The predicate receives the source row and the source parent index.
        Return True to accept, False to reject. If None, only column filters
        are applied.
        """
        self._row_predicate = predicate
        self.invalidateFilter()

    def set_numeric_sort_column(
        self, column: int, extractor: Optional[Callable[[Any], str]] = None
    ) -> None:
        """Enable numeric-aware sorting for a column.

        If ``extractor`` is provided it is used to convert the display value to
        a string to be interpreted as an integer when possible.
        """
        if extractor is None:
            self._numeric_sort_extractors[column] = lambda v: (
                "" if v is None else str(v)
            )
        else:
            self._numeric_sort_extractors[column] = extractor

    def filterAcceptsRow(
        self, source_row: int, source_parent: QModelIndex
    ) -> bool:
        model = self.sourceModel()
        if model is None:
            return True

        # Apply per-column regex filters
        for col, rx in self._column_filters.items():
            idx = model.index(source_row, col, source_parent)
            if not idx.isValid():
                return False

            val = model.data(idx, Qt.ItemDataRole.DisplayRole)
            text = "" if val is None else str(val)
            if not rx.indexIn(text) >= 0:
                return False

        # Optional full-row predicate (e.g., full-text search)
        if self._row_predicate is not None:
            try:
                if not self._row_predicate(
                    source_row, source_parent, self.filterCaseSensitivity()
                ):
                    return False
            except Exception:
                logger.exception("Row predicate failed at row %d", source_row)
                return False

        return True

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        insensitive = (
            self.filterCaseSensitivity() == Qt.CaseSensitivity.CaseInsensitive
        )
        col = left.column()
        model = self.sourceModel()
        if model is None:
            return super().lessThan(left, right)

        lv = model.data(left, SORT_ROLE)
        if lv is None:
            lv = model.data(left, Qt.ItemDataRole.DisplayRole)
        rv = model.data(right, SORT_ROLE)
        if rv is None:
            rv = model.data(right, Qt.ItemDataRole.DisplayRole)

        extractor = self._numeric_sort_extractors.get(col)
        if extractor is not None:
            ls = extractor(lv)
            rs = extractor(rv)

            def to_int(s: str):
                """As the user sets this explicitly, we can assume it is a
                valid integer.
                """
                try:
                    return int(str(s).strip())
                except Exception:
                    return None

            li = to_int(ls)
            ri = to_int(rs)
            if li is not None and ri is not None:
                return li < ri

            # Fallback to case-insensitive string compare
            if insensitive:
                return (ls or "").casefold() < (rs or "").casefold()
            else:
                return (ls or "") < (rs or "")

        return super().lessThan(left, right)
