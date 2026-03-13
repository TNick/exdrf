"""Tests for proxy module."""

import os
import unittest
from unittest.mock import MagicMock

from PyQt6.QtCore import QModelIndex, QObject, Qt
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QApplication

from exdrf_qt.models.proxy import SORT_ROLE, ProxyModel

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if QApplication.instance() is None:
    QApplication([])


def _make_source_model(
    rows: list,
    sort_values: list | None = None,
) -> QStandardItemModel:
    """Build a QStandardItemModel with one column and given row data."""
    model = QStandardItemModel()
    for i, val in enumerate(rows):
        item = QStandardItem()
        if val is not None:
            item.setData(val, Qt.ItemDataRole.DisplayRole)
        if sort_values is not None and i < len(sort_values):
            item.setData(sort_values[i], SORT_ROLE)
        model.setItem(i, 0, item)
    return model


class TestProxyModelInit(unittest.TestCase):
    """Tests for ProxyModel initialization."""

    def test_init_default(self) -> None:
        """Test initialization with default values."""
        proxy = ProxyModel()
        self.assertEqual(len(proxy._column_filters), 0)
        self.assertIsNone(proxy._row_predicate)
        self.assertEqual(
            proxy.filterCaseSensitivity(),
            Qt.CaseSensitivity.CaseInsensitive,
        )
        self.assertEqual(len(proxy._numeric_sort_extractors), 0)

    def test_init_with_parent(self) -> None:
        """Test initialization with parent."""
        parent = QObject()
        proxy = ProxyModel(parent)
        self.assertIs(proxy.parent(), parent)


class TestProxyModelSetFilterCaseSensitivity(unittest.TestCase):
    """Tests for ProxyModel.setFilterCaseSensitivity method."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.proxy = ProxyModel()
        self.proxy.set_column_filter(0, "test")

    def test_set_filter_case_sensitivity_updates_filters(self) -> None:
        """Test setting case sensitivity updates existing filters."""
        self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseSensitive)
        self.assertEqual(
            self.proxy.filterCaseSensitivity(),
            Qt.CaseSensitivity.CaseSensitive,
        )
        self.assertIn(0, self.proxy._column_filters)

    def test_set_filter_case_sensitivity_preserves_patterns(self) -> None:
        """Test setting case sensitivity preserves filter patterns."""
        self.proxy.set_column_filter(0, "test.*")
        original_pattern = self.proxy._column_filters[0].pattern()
        self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseSensitive)
        self.assertEqual(
            self.proxy._column_filters[0].pattern(), original_pattern
        )


class TestProxyModelSetColumnFilter(unittest.TestCase):
    """Tests for ProxyModel.set_column_filter method."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.proxy = ProxyModel()
        self.proxy.invalidateFilter = MagicMock()

    def test_set_column_filter_with_text(self) -> None:
        """Test setting column filter with text."""
        self.proxy.set_column_filter(0, "test")
        self.assertIn(0, self.proxy._column_filters)
        self.proxy.invalidateFilter.assert_called_once()

    def test_set_column_filter_empty_removes(self) -> None:
        """Test setting empty filter text removes the filter."""
        self.proxy.set_column_filter(0, "test")
        self.proxy.set_column_filter(0, "")
        self.assertNotIn(0, self.proxy._column_filters)

    def test_set_column_filter_multiple_columns(self) -> None:
        """Test setting filters on multiple columns."""
        self.proxy.set_column_filter(0, "col0")
        self.proxy.set_column_filter(1, "col1")
        self.assertIn(0, self.proxy._column_filters)
        self.assertIn(1, self.proxy._column_filters)
        self.assertEqual(len(self.proxy._column_filters), 2)


class TestProxyModelSetRowPredicate(unittest.TestCase):
    """Tests for ProxyModel.set_row_predicate method."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.proxy = ProxyModel()
        self.proxy.invalidateFilter = MagicMock()

    def test_set_row_predicate(self) -> None:
        """Test setting row predicate."""
        predicate = MagicMock(return_value=True)
        self.proxy.set_row_predicate(predicate)
        self.assertEqual(self.proxy._row_predicate, predicate)
        self.proxy.invalidateFilter.assert_called_once()

    def test_set_row_predicate_none(self) -> None:
        """Test clearing row predicate."""
        predicate = MagicMock(return_value=True)
        self.proxy.set_row_predicate(predicate)
        self.proxy.set_row_predicate(None)
        self.assertIsNone(self.proxy._row_predicate)


class TestProxyModelSetNumericSortColumn(unittest.TestCase):
    """Tests for ProxyModel.set_numeric_sort_column method."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.proxy = ProxyModel()

    def test_set_numeric_sort_column_default_extractor(self) -> None:
        """Test setting numeric sort with default extractor."""
        self.proxy.set_numeric_sort_column(0)
        self.assertIn(0, self.proxy._numeric_sort_extractors)
        extractor = self.proxy._numeric_sort_extractors[0]
        self.assertEqual(extractor(None), "")
        self.assertEqual(extractor(123), "123")

    def test_set_numeric_sort_column_custom_extractor(self) -> None:
        """Test setting numeric sort with custom extractor."""

        def extractor(v):
            return str(v) if v else "0"

        self.proxy.set_numeric_sort_column(0, extractor)
        self.assertEqual(self.proxy._numeric_sort_extractors[0], extractor)


class TestProxyModelFilterAcceptsRow(unittest.TestCase):
    """Tests for ProxyModel.filterAcceptsRow method."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.proxy = ProxyModel()

    def test_filter_accepts_row_no_source_model(self) -> None:
        """Test filter accepts row when no source model."""
        self.proxy.setSourceModel(None)
        result = self.proxy.filterAcceptsRow(0, QModelIndex())
        self.assertTrue(result)

    def test_filter_accepts_row_no_filters(self) -> None:
        """Test filter accepts row when no filters are set."""
        source = _make_source_model(["any"])
        self.proxy.setSourceModel(source)
        self.proxy._row_predicate = None
        result = self.proxy.filterAcceptsRow(0, QModelIndex())
        self.assertTrue(result)

    def test_filter_accepts_row_column_filter_matches(self) -> None:
        """Test filter accepts row when column filter matches."""
        source = _make_source_model(["test value"])
        self.proxy.setSourceModel(source)
        self.proxy.set_column_filter(0, "test")
        self.proxy._row_predicate = None
        result = self.proxy.filterAcceptsRow(0, QModelIndex())
        self.assertTrue(result)

    def test_filter_accepts_row_column_filter_no_match(self) -> None:
        """Test filter rejects row when column filter doesn't match."""
        source = _make_source_model(["other value"])
        self.proxy.setSourceModel(source)
        self.proxy.set_column_filter(0, "test")
        self.proxy._row_predicate = None
        result = self.proxy.filterAcceptsRow(0, QModelIndex())
        self.assertFalse(result)

    def test_filter_accepts_row_invalid_index(self) -> None:
        """Test filter rejects row when index is invalid."""
        source = _make_source_model([])
        self.proxy.setSourceModel(source)
        self.proxy.set_column_filter(0, "test")
        result = self.proxy.filterAcceptsRow(0, QModelIndex())
        self.assertFalse(result)

    def test_filter_accepts_row_with_predicate_accepts(self) -> None:
        """Test filter accepts row when predicate accepts."""
        source = _make_source_model(["x"])
        self.proxy.setSourceModel(source)
        predicate = MagicMock(return_value=True)
        self.proxy.set_row_predicate(predicate)
        result = self.proxy.filterAcceptsRow(0, QModelIndex())
        self.assertTrue(result)
        predicate.assert_called_once()

    def test_filter_accepts_row_with_predicate_rejects(self) -> None:
        """Test filter rejects row when predicate rejects."""
        source = _make_source_model(["x"])
        self.proxy.setSourceModel(source)
        predicate = MagicMock(return_value=False)
        self.proxy.set_row_predicate(predicate)
        result = self.proxy.filterAcceptsRow(0, QModelIndex())
        self.assertFalse(result)

    def test_filter_accepts_row_predicate_exception(self) -> None:
        """Test filter handles predicate exception."""
        source = _make_source_model(["x"])
        self.proxy.setSourceModel(source)
        predicate = MagicMock(side_effect=Exception("Test error"))
        self.proxy.set_row_predicate(predicate)
        result = self.proxy.filterAcceptsRow(0, QModelIndex())
        self.assertFalse(result)

    def test_filter_accepts_row_none_value(self) -> None:
        """Test filter handles None values in data."""
        source = _make_source_model([None])
        self.proxy.setSourceModel(source)
        self.proxy.set_column_filter(0, ".*")
        self.proxy._row_predicate = None
        result = self.proxy.filterAcceptsRow(0, QModelIndex())
        self.assertTrue(result)


class TestProxyModelLessThan(unittest.TestCase):
    """Tests for ProxyModel.lessThan method."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.proxy = ProxyModel()

    def test_less_than_no_source_model(self) -> None:
        """Test lessThan delegates to parent when no source model."""
        self.proxy.setSourceModel(None)
        left = QModelIndex()
        right = QModelIndex()
        result = self.proxy.lessThan(left, right)
        self.assertIsInstance(result, bool)

    def test_less_than_uses_sort_role(self) -> None:
        """Test lessThan uses SORT_ROLE when available."""
        source = _make_source_model(
            ["a", "b"],
            sort_values=["sort_a", "sort_b"],
        )
        self.proxy.setSourceModel(source)
        left = source.index(0, 0, QModelIndex())
        right = source.index(1, 0, QModelIndex())
        result = self.proxy.lessThan(left, right)
        self.assertTrue(result)  # "sort_a" < "sort_b"

    def test_less_than_falls_back_to_display_role(self) -> None:
        """Test lessThan falls back to DisplayRole when SORT_ROLE is None."""
        source = _make_source_model(["apple", "banana"])
        self.proxy.setSourceModel(source)
        left = source.index(0, 0, QModelIndex())
        right = source.index(1, 0, QModelIndex())
        result = self.proxy.lessThan(left, right)
        self.assertTrue(result)  # "apple" < "banana"

    def test_less_than_numeric_sorting(self) -> None:
        """Test lessThan with numeric sorting enabled."""
        source = _make_source_model(["5", "10"])
        self.proxy.setSourceModel(source)
        self.proxy.set_numeric_sort_column(0)
        left = source.index(0, 0, QModelIndex())
        right = source.index(1, 0, QModelIndex())
        result = self.proxy.lessThan(left, right)
        self.assertTrue(result)  # 5 < 10

    def test_less_than_numeric_sorting_parses_integers(self) -> None:
        """Test lessThan numeric sorting parses integers correctly."""
        source = _make_source_model(["10", "2"])
        self.proxy.setSourceModel(source)
        self.proxy.set_numeric_sort_column(0)
        left = source.index(0, 0, QModelIndex())
        right = source.index(1, 0, QModelIndex())
        result = self.proxy.lessThan(left, right)
        self.assertFalse(result)  # 10 is not < 2

    def test_less_than_numeric_sorting_non_numeric_fallback(self) -> None:
        """Test lessThan numeric sorting falls back to string compare."""
        source = _make_source_model(["abc", "xyz"])
        self.proxy.setSourceModel(source)
        self.proxy.set_numeric_sort_column(0)
        self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        left = source.index(0, 0, QModelIndex())
        right = source.index(1, 0, QModelIndex())
        result = self.proxy.lessThan(left, right)
        self.assertTrue(result)  # "abc" < "xyz"

    def test_less_than_case_sensitive_string_comparison(self) -> None:
        """Test lessThan with case sensitive string comparison."""
        source = _make_source_model(["A", "a"])
        self.proxy.setSourceModel(source)
        self.proxy.set_numeric_sort_column(0)
        self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseSensitive)
        left = source.index(0, 0, QModelIndex())
        right = source.index(1, 0, QModelIndex())
        result = self.proxy.lessThan(left, right)
        self.assertTrue(result)  # "A" < "a" in ASCII

    def test_less_than_case_insensitive_string_comparison(self) -> None:
        """Test lessThan with case insensitive string comparison."""
        source = _make_source_model(["apple", "banana"])
        self.proxy.setSourceModel(source)
        self.proxy.set_numeric_sort_column(0)
        self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        left = source.index(0, 0, QModelIndex())
        right = source.index(1, 0, QModelIndex())
        result = self.proxy.lessThan(left, right)
        self.assertTrue(result)  # "apple" < "banana"
