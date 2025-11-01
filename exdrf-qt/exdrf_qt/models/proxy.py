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
        _numeric_sort_extractors: Map of column to extractor function for
            numeric-aware sorting.
    """

    _column_filters: Dict[int, QRegExp]
    _row_predicate: Optional[
        Callable[[int, QModelIndex, Qt.CaseSensitivity], bool]
    ]
    _numeric_sort_extractors: Dict[int, Callable[[Any], str]]

    def __init__(self, parent=None) -> None:
        """Initialize the proxy model.

        Sets up empty column filters, no row predicate, case-insensitive
        filtering by default, and empty numeric sort extractors.

        Args:
            parent: The parent QObject, if any.
        """
        super().__init__(parent)
        self._column_filters = {}
        self._row_predicate = None
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._numeric_sort_extractors = {}

    def setFilterCaseSensitivity(self, cs: Qt.CaseSensitivity) -> None:
        """Set the case sensitivity for filtering.

        Updates all existing column filters to use the new case sensitivity
        and calls the parent method to update the base filter sensitivity.

        Args:
            cs: The case sensitivity to use for filtering.
        """
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

        The predicate receives the source row index, source parent index,
        and current case sensitivity. Return True to accept the row, False
        to reject. If None, only column filters are applied.

        Args:
            predicate: Optional callable that takes (source_row, source_parent,
                case_sensitivity) and returns bool, or None to clear the predicate.
        """
        self._row_predicate = predicate
        self.invalidateFilter()

    def set_numeric_sort_column(
        self, column: int, extractor: Optional[Callable[[Any], str]] = None
    ) -> None:
        """Enable numeric-aware sorting for a column.

        When sorting this column, values are converted to strings and then
        parsed as integers when possible. Non-numeric values fall back to
        string comparison.

        Args:
            column: The column index to enable numeric sorting for.
            extractor: Optional callable to convert display values to strings.
                If None, uses a default converter that handles None values.
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
        """Determine if a row should be included in the filtered model.

        Applies all active column filters first, then the optional row predicate.
        A row is accepted only if all column filters match and the row predicate
        (if set) returns True.

        Args:
            source_row: The row index in the source model.
            source_parent: The parent index in the source model.

        Returns:
            True if the row should be included, False otherwise.
        """
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
        """Compare two indices for sorting purposes.

        Uses SORT_ROLE data if available, otherwise falls back to DisplayRole.
        For columns with numeric sorting enabled, attempts to parse values as
        integers. Falls back to string comparison if numeric parsing fails or
        numeric sorting is not enabled.

        Args:
            left: The left index to compare.
            right: The right index to compare.

        Returns:
            True if left should sort before right, False otherwise.
        """
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

            def to_int(s: str) -> Optional[int]:
                """Convert string to integer if possible.

                Args:
                    s: The string to convert.

                Returns:
                    The integer value, or None if conversion fails.
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
