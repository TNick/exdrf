"""Tests for model module."""

import unittest
from unittest.mock import MagicMock, patch

from exdrf.filter import FieldFilter
from PyQt5.QtCore import QModelIndex, Qt

from exdrf_qt.models.model import QtModel, compare_filters


class TestCompareFilters(unittest.TestCase):
    """Tests for compare_filters function."""

    def test_compare_filters_equal_dicts(self) -> None:
        """Test comparing equal filter dictionaries."""
        f1 = {"fld": "name", "op": "==", "vl": "test"}
        f2 = {"fld": "name", "op": "==", "vl": "test"}
        self.assertTrue(compare_filters(f1, f2))

    def test_compare_filters_unequal_dicts(self) -> None:
        """Test comparing unequal filter dictionaries."""
        f1 = {"fld": "name", "op": "==", "vl": "test"}
        f2 = {"fld": "name", "op": "==", "vl": "other"}
        self.assertFalse(compare_filters(f1, f2))

    def test_compare_filters_equal_field_filters(self) -> None:
        """Test comparing equal FieldFilter objects."""
        f1 = FieldFilter(fld="name", op="==", vl="test")
        f2 = FieldFilter(fld="name", op="==", vl="test")
        self.assertTrue(compare_filters(f1, f2))

    def test_compare_filters_unequal_field_filters(self) -> None:
        """Test comparing unequal FieldFilter objects."""
        f1 = FieldFilter(fld="name", op="==", vl="test")
        f2 = FieldFilter(fld="name", op="!=", vl="test")
        self.assertFalse(compare_filters(f1, f2))

    def test_compare_filters_equal_lists(self) -> None:
        """Test comparing equal filter lists."""
        f1 = ["OR", [{"fld": "name", "op": "==", "vl": "test"}]]
        f2 = ["OR", [{"fld": "name", "op": "==", "vl": "test"}]]
        self.assertTrue(compare_filters(f1, f2))

    def test_compare_filters_unequal_list_lengths(self) -> None:
        """Test comparing filter lists with different lengths."""
        f1 = ["OR", [{"fld": "name", "op": "==", "vl": "test"}]]
        f2 = [
            "OR",
            [
                {"fld": "name", "op": "==", "vl": "test"},
                {"fld": "id", "op": "==", "vl": 1},
            ],
        ]
        self.assertFalse(compare_filters(f1, f2))

    def test_compare_filters_nested_lists(self) -> None:
        """Test comparing nested filter lists."""
        f1 = [
            "AND",
            [
                {"fld": "name", "op": "==", "vl": "test"},
                {"fld": "id", "op": ">", "vl": 0},
            ],
        ]
        f2 = [
            "AND",
            [
                {"fld": "name", "op": "==", "vl": "test"},
                {"fld": "id", "op": ">", "vl": 0},
            ],
        ]
        self.assertTrue(compare_filters(f1, f2))

    def test_compare_filters_mixed_types(self) -> None:
        """Test comparing filters with mixed dict and FieldFilter."""
        f1 = {"fld": "name", "op": "==", "vl": "test"}
        f2 = FieldFilter(fld="name", op="==", vl="test")
        self.assertTrue(compare_filters(f1, f2))


class TestQtModelRowCount(unittest.TestCase):
    """Tests for QtModel.rowCount method."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_ctx = MagicMock()
        self.mock_db_model = MagicMock()
        self.model = QtModel(
            ctx=self.mock_ctx,
            db_model=self.mock_db_model,
            prevent_total_count=True,
        )
        self.model._total_count = 10
        self.model.top_cache = [MagicMock(), MagicMock()]

    def test_row_count_invalid_parent(self) -> None:
        """Test rowCount with invalid parent returns total count."""
        parent = QModelIndex()
        result = self.model.rowCount(parent)
        self.assertEqual(result, 12)  # 10 + 2 top_cache items

    def test_row_count_valid_parent(self) -> None:
        """Test rowCount with valid parent returns 0."""
        parent = self.model.createIndex(0, 0)
        result = self.model.rowCount(parent)
        self.assertEqual(result, 0)


class TestQtModelColumnCount(unittest.TestCase):
    """Tests for QtModel.columnCount method."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_ctx = MagicMock()
        self.mock_db_model = MagicMock()
        self.mock_field1 = MagicMock()
        self.mock_field2 = MagicMock()
        self.model = QtModel(
            ctx=self.mock_ctx,
            db_model=self.mock_db_model,
            prevent_total_count=True,
        )
        self.model.column_fields = [self.mock_field1, self.mock_field2]

    def test_column_count(self) -> None:
        """Test columnCount returns number of column fields."""
        parent = QModelIndex()
        result = self.model.columnCount(parent)
        self.assertEqual(result, 2)


class TestQtModelHasChildren(unittest.TestCase):
    """Tests for QtModel.hasChildren method."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_ctx = MagicMock()
        self.mock_db_model = MagicMock()
        self.model = QtModel(
            ctx=self.mock_ctx,
            db_model=self.mock_db_model,
            prevent_total_count=True,
        )

    def test_has_children_invalid_parent(self) -> None:
        """Test hasChildren with invalid parent returns True."""
        parent = QModelIndex()
        result = self.model.hasChildren(parent)
        self.assertTrue(result)

    def test_has_children_valid_parent(self) -> None:
        """Test hasChildren with valid parent returns False."""
        parent = self.model.createIndex(0, 0)
        result = self.model.hasChildren(parent)
        self.assertFalse(result)


class TestQtModelParent(unittest.TestCase):
    """Tests for QtModel.parent method."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_ctx = MagicMock()
        self.mock_db_model = MagicMock()
        self.model = QtModel(
            ctx=self.mock_ctx,
            db_model=self.mock_db_model,
            prevent_total_count=True,
        )

    def test_parent_always_invalid(self) -> None:
        """Test parent always returns invalid index."""
        child = self.model.createIndex(0, 0)
        result = self.model.parent(child)
        self.assertFalse(result.isValid())


class TestQtModelIndex(unittest.TestCase):
    """Tests for QtModel.index method."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_ctx = MagicMock()
        self.mock_db_model = MagicMock()
        self.model = QtModel(
            ctx=self.mock_ctx,
            db_model=self.mock_db_model,
            prevent_total_count=True,
        )
        self.model._total_count = 10

    def test_index_valid(self) -> None:
        """Test index with valid parameters."""
        parent = QModelIndex()
        result = self.model.index(0, 0, parent)
        self.assertTrue(result.isValid())
        self.assertEqual(result.row(), 0)
        self.assertEqual(result.column(), 0)

    def test_index_invalid_parent(self) -> None:
        """Test index with valid parent returns invalid."""
        parent = self.model.createIndex(0, 0)
        result = self.model.index(0, 0, parent)
        self.assertFalse(result.isValid())

    def test_index_out_of_range(self) -> None:
        """Test index with out of range returns invalid."""
        parent = QModelIndex()
        result = self.model.index(100, 0, parent)
        self.assertFalse(result.isValid())


class TestQtModelName(unittest.TestCase):
    """Tests for QtModel.name property."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_ctx = MagicMock()
        self.mock_db_model = MagicMock()
        self.mock_db_model.__name__ = "TestModel"
        self.model = QtModel(
            ctx=self.mock_ctx,
            db_model=self.mock_db_model,
            prevent_total_count=True,
        )

    def test_name(self) -> None:
        """Test name property returns db_model name."""
        self.assertEqual(self.model.name, "TestModel")


class TestQtModelFlags(unittest.TestCase):
    """Tests for QtModel.flags method."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_ctx = MagicMock()
        self.mock_db_model = MagicMock()
        self.model = QtModel(
            ctx=self.mock_ctx,
            db_model=self.mock_db_model,
            prevent_total_count=True,
        )

    def test_flags_invalid_index(self) -> None:
        """Test flags with invalid index returns NoItemFlags."""
        index = QModelIndex()
        result = self.model.flags(index)
        self.assertEqual(result, Qt.ItemFlag.NoItemFlags)

    def test_flags_valid_index_not_checkable(self) -> None:
        """Test flags with valid index when not checkable."""
        index = self.model.createIndex(0, 0)
        result = self.model.flags(index)
        expected = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        self.assertEqual(result, expected)

    def test_flags_valid_index_checkable(self) -> None:
        """Test flags with valid index when checkable."""
        self.model._checked = set()
        index = self.model.createIndex(0, 0)
        result = self.model.flags(index)
        expected = (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsUserCheckable
        )
        self.assertEqual(result, expected)


class TestQtModelIsFullyLoaded(unittest.TestCase):
    """Tests for QtModel.is_fully_loaded property."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_ctx = MagicMock()
        self.mock_db_model = MagicMock()
        self.model = QtModel(
            ctx=self.mock_ctx,
            db_model=self.mock_db_model,
            prevent_total_count=True,
        )

    def test_is_fully_loaded_true(self) -> None:
        """Test is_fully_loaded when all items are loaded."""
        self.model._total_count = 10
        self.model._loaded_count = 10
        self.assertTrue(self.model.is_fully_loaded)

    def test_is_fully_loaded_false(self) -> None:
        """Test is_fully_loaded when not all items are loaded."""
        self.model._total_count = 10
        self.model._loaded_count = 5
        self.assertFalse(self.model.is_fully_loaded)


class TestQtModelCheckedIds(unittest.TestCase):
    """Tests for QtModel.checked_ids property."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_ctx = MagicMock()
        self.mock_db_model = MagicMock()
        self.model = QtModel(
            ctx=self.mock_ctx,
            db_model=self.mock_db_model,
            prevent_total_count=True,
        )

    def test_checked_ids_none_when_not_checkable(self) -> None:
        """Test checked_ids returns None when not in checkable mode."""
        self.assertIsNone(self.model.checked_ids)

    def test_checked_ids_returns_set(self) -> None:
        """Test checked_ids returns the set when in checkable mode."""
        checked_set = {1, 2, 3}
        self.model._checked = checked_set
        self.assertEqual(self.model.checked_ids, checked_set)

    def test_checked_ids_setter(self) -> None:
        """Test setting checked_ids."""
        checked_set = {1, 2, 3}
        self.model.checked_ids = checked_set
        self.assertEqual(self.model._checked, checked_set)


class TestQtModelDataRecord(unittest.TestCase):
    """Tests for QtModel.data_record method."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_ctx = MagicMock()
        self.mock_db_model = MagicMock()
        self.model = QtModel(
            ctx=self.mock_ctx,
            db_model=self.mock_db_model,
            prevent_total_count=True,
        )
        self.mock_record1 = MagicMock()
        self.mock_record2 = MagicMock()
        self.model.top_cache = [self.mock_record1, self.mock_record2]
        self.model._total_count = 5
        self.model.cache.set_size(5)
        self.model.cache[0] = MagicMock()

    def test_data_record_from_top_cache(self) -> None:
        """Test data_record returns record from top_cache."""
        result = self.model.data_record(0)
        self.assertEqual(result, self.mock_record1)

    def test_data_record_from_cache(self) -> None:
        """Test data_record returns record from cache."""
        result = self.model.data_record(2)
        self.assertEqual(result, self.model.cache[0])

    def test_data_record_negative_row(self) -> None:
        """Test data_record returns None for negative row."""
        result = self.model.data_record(-1)
        self.assertIsNone(result)

    def test_data_record_out_of_range(self) -> None:
        """Test data_record returns None for out of range row."""
        result = self.model.data_record(100)
        self.assertIsNone(result)


class TestQtModelCloneMe(unittest.TestCase):
    """Tests for QtModel.clone_me method."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_ctx = MagicMock()
        self.mock_db_model = MagicMock()
        self.model = QtModel(
            ctx=self.mock_ctx,
            db_model=self.mock_db_model,
            prevent_total_count=True,
        )
        self.model._filters = [{"fld": "name", "op": "==", "vl": "test"}]
        self.model.sort_by = [("name", "asc")]
        self.model.top_cache = [MagicMock()]
        self.model.base_selection = MagicMock()

    @patch("exdrf_qt.models.model.QtModel.recalculate_total_count")
    def test_clone_me(self, mock_recalc: MagicMock) -> None:
        """Test clone_me creates a clone with same attributes."""
        mock_recalc.return_value = 10
        clone = self.model.clone_me()
        self.assertEqual(clone.ctx, self.model.ctx)
        self.assertEqual(clone.db_model, self.model.db_model)
        self.assertEqual(clone.base_selection, self.model.base_selection)
        self.assertEqual(clone._filters, self.model._filters)
        self.assertEqual(clone.sort_by, self.model.sort_by)
        self.assertEqual(clone.top_cache, self.model.top_cache)


class TestQtModelCheckedRows(unittest.TestCase):
    """Tests for QtModel.checked_rows method."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_ctx = MagicMock()
        self.mock_db_model = MagicMock()
        self.model = QtModel(
            ctx=self.mock_ctx,
            db_model=self.mock_db_model,
            prevent_total_count=True,
        )
        self.model.top_cache = [MagicMock()]

    def test_checked_rows_none_when_not_checkable(self) -> None:
        """Test checked_rows returns None when not checkable."""
        self.assertIsNone(self.model.checked_rows())

    def test_checked_rows_with_mapping(self) -> None:
        """Test checked_rows returns correct row indices."""
        self.model._checked = {1, 2}
        self.model._db_to_row = {1: 0, 2: 5}
        result = self.model.checked_rows()
        self.assertEqual(result, [1, 6])  # 0+1, 5+1 (top_cache offset)


class TestQtModelSetPrioritizedIds(unittest.TestCase):
    """Tests for QtModel.set_prioritized_ids method."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_ctx = MagicMock()
        self.mock_db_model = MagicMock()
        self.model = QtModel(
            ctx=self.mock_ctx,
            db_model=self.mock_db_model,
            prevent_total_count=True,
        )

    @patch("exdrf_qt.models.model.QtModel.reset_model")
    def test_set_prioritized_ids_changes_value(
        self, mock_reset: MagicMock
    ) -> None:
        """Test set_prioritized_ids sets value and resets model."""
        ids = [1, 2, 3]
        self.model.set_prioritized_ids(ids)
        self.assertEqual(self.model.prioritized_ids, ids)
        mock_reset.assert_called_once()

    @patch("exdrf_qt.models.model.QtModel.reset_model")
    def test_set_prioritized_ids_same_value_no_reset(
        self, mock_reset: MagicMock
    ) -> None:
        """Test set_prioritized_ids does not reset if same value."""
        ids = [1, 2, 3]
        self.model.prioritized_ids = ids
        self.model.set_prioritized_ids(ids)
        mock_reset.assert_not_called()
