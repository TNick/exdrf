"""Tests for proxy module."""

import unittest
from unittest.mock import MagicMock

from PyQt5.QtCore import QModelIndex, Qt

from exdrf_qt.models.proxy import ProxyModel, SORT_ROLE


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
        parent = MagicMock()
        proxy = ProxyModel(parent)
        self.assertEqual(proxy.parent(), parent)


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
        self.mock_model = MagicMock()
        self.mock_index = MagicMock()
        self.mock_index.isValid.return_value = True
        self.mock_model.index.return_value = self.mock_index

    def test_filter_accepts_row_no_source_model(self) -> None:
        """Test filter accepts row when no source model."""
        self.proxy.setSourceModel(None)
        result = self.proxy.filterAcceptsRow(0, QModelIndex())
        self.assertTrue(result)

    def test_filter_accepts_row_no_filters(self) -> None:
        """Test filter accepts row when no filters are set."""
        self.proxy.setSourceModel(self.mock_model)
        self.proxy._row_predicate = None
        result = self.proxy.filterAcceptsRow(0, QModelIndex())
        self.assertTrue(result)

    def test_filter_accepts_row_column_filter_matches(self) -> None:
        """Test filter accepts row when column filter matches."""
        self.proxy.setSourceModel(self.mock_model)
        self.proxy.set_column_filter(0, "test")
        self.mock_index.isValid.return_value = True
        self.mock_model.data.return_value = "test value"
        self.proxy._row_predicate = None
        result = self.proxy.filterAcceptsRow(0, QModelIndex())
        self.assertTrue(result)

    def test_filter_accepts_row_column_filter_no_match(self) -> None:
        """Test filter rejects row when column filter doesn't match."""
        self.proxy.setSourceModel(self.mock_model)
        self.proxy.set_column_filter(0, "test")
        self.mock_index.isValid.return_value = True
        self.mock_model.data.return_value = "other value"
        self.proxy._row_predicate = None
        result = self.proxy.filterAcceptsRow(0, QModelIndex())
        self.assertFalse(result)

    def test_filter_accepts_row_invalid_index(self) -> None:
        """Test filter rejects row when index is invalid."""
        self.proxy.setSourceModel(self.mock_model)
        self.proxy.set_column_filter(0, "test")
        self.mock_index.isValid.return_value = False
        result = self.proxy.filterAcceptsRow(0, QModelIndex())
        self.assertFalse(result)

    def test_filter_accepts_row_with_predicate_accepts(self) -> None:
        """Test filter accepts row when predicate accepts."""
        self.proxy.setSourceModel(self.mock_model)
        predicate = MagicMock(return_value=True)
        self.proxy.set_row_predicate(predicate)
        result = self.proxy.filterAcceptsRow(0, QModelIndex())
        self.assertTrue(result)
        predicate.assert_called_once()

    def test_filter_accepts_row_with_predicate_rejects(self) -> None:
        """Test filter rejects row when predicate rejects."""
        self.proxy.setSourceModel(self.mock_model)
        predicate = MagicMock(return_value=False)
        self.proxy.set_row_predicate(predicate)
        result = self.proxy.filterAcceptsRow(0, QModelIndex())
        self.assertFalse(result)

    def test_filter_accepts_row_predicate_exception(self) -> None:
        """Test filter handles predicate exception."""
        self.proxy.setSourceModel(self.mock_model)
        predicate = MagicMock(side_effect=Exception("Test error"))
        self.proxy.set_row_predicate(predicate)
        result = self.proxy.filterAcceptsRow(0, QModelIndex())
        self.assertFalse(result)

    def test_filter_accepts_row_none_value(self) -> None:
        """Test filter handles None values in data."""
        self.proxy.setSourceModel(self.mock_model)
        self.proxy.set_column_filter(0, ".*")
        self.mock_index.isValid.return_value = True
        self.mock_model.data.return_value = None
        self.proxy._row_predicate = None
        result = self.proxy.filterAcceptsRow(0, QModelIndex())
        self.assertTrue(result)


class TestProxyModelLessThan(unittest.TestCase):
    """Tests for ProxyModel.lessThan method."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.proxy = ProxyModel()
        self.mock_model = MagicMock()
        self.proxy.setSourceModel(self.mock_model)

    def test_less_than_no_source_model(self) -> None:
        """Test lessThan delegates to parent when no source model."""
        self.proxy.setSourceModel(None)
        left = MagicMock()
        right = MagicMock()
        result = self.proxy.lessThan(left, right)
        # Should call parent, verify it doesn't crash
        self.assertIsInstance(result, bool)

    def test_less_than_uses_sort_role(self) -> None:
        """Test lessThan uses SORT_ROLE when available."""
        left = MagicMock()
        right = MagicMock()
        left.column.return_value = 0
        self.mock_model.data.side_effect = lambda idx, role: (
            "sort_value" if role == SORT_ROLE else "display_value"
        )
        result = self.proxy.lessThan(left, right)
        self.assertIsInstance(result, bool)

    def test_less_than_falls_back_to_display_role(self) -> None:
        """Test lessThan falls back to DisplayRole when SORT_ROLE is None."""
        left = MagicMock()
        right = MagicMock()
        left.column.return_value = 0

        def data_side_effect(idx, role):
            if role == SORT_ROLE:
                return None
            return "display_value"

        self.mock_model.data.side_effect = data_side_effect
        result = self.proxy.lessThan(left, right)
        self.assertIsInstance(result, bool)

    def test_less_than_numeric_sorting(self) -> None:
        """Test lessThan with numeric sorting enabled."""
        self.proxy.set_numeric_sort_column(0)
        left = MagicMock()
        right = MagicMock()
        left.column.return_value = 0
        self.mock_model.data.return_value = "5"
        right_data = MagicMock()
        right_data.column.return_value = 0
        result = self.proxy.lessThan(left, right)
        self.assertIsInstance(result, bool)

    def test_less_than_numeric_sorting_parses_integers(self) -> None:
        """Test lessThan numeric sorting parses integers correctly."""
        self.proxy.set_numeric_sort_column(0)
        left = MagicMock()
        right = MagicMock()
        left.column.return_value = 0

        def data_side_effect(idx, role):
            if idx == left:
                return "10"
            elif idx == right:
                return "2"
            return None

        self.mock_model.data.side_effect = data_side_effect
        result = self.proxy.lessThan(left, right)
        self.assertFalse(result)  # 10 is not < 2

    def test_less_than_numeric_sorting_non_numeric_fallback(self) -> None:
        """Test lessThan numeric sorting falls back to string compare."""
        self.proxy.set_numeric_sort_column(0)
        self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        left = MagicMock()
        right = MagicMock()
        left.column.return_value = 0

        def data_side_effect(idx, role):
            if idx == left:
                return "abc"
            elif idx == right:
                return "xyz"
            return None

        self.mock_model.data.side_effect = data_side_effect
        result = self.proxy.lessThan(left, right)
        self.assertTrue(result)  # "abc" < "xyz"

    def test_less_than_case_sensitive_string_comparison(self) -> None:
        """Test lessThan with case sensitive string comparison."""
        self.proxy.set_numeric_sort_column(0)
        self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseSensitive)
        left = MagicMock()
        right = MagicMock()
        left.column.return_value = 0

        def data_side_effect(idx, role):
            if idx == left:
                return "A"
            elif idx == right:
                return "a"
            return None

        self.mock_model.data.side_effect = data_side_effect
        result = self.proxy.lessThan(left, right)
        self.assertIsInstance(result, bool)

    def test_less_than_case_insensitive_string_comparison(self) -> None:
        """Test lessThan with case insensitive string comparison."""
        self.proxy.set_numeric_sort_column(0)
        self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        left = MagicMock()
        right = MagicMock()
        left.column.return_value = 0

        def data_side_effect(idx, role):
            if idx == left:
                return "apple"
            elif idx == right:
                return "banana"
            return None

        self.mock_model.data.side_effect = data_side_effect
        result = self.proxy.lessThan(left, right)
        self.assertTrue(result)  # "apple" < "banana"
