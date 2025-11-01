"""Tests for exdrf_qt.models.record module."""

import unittest
from unittest.mock import MagicMock

from PyQt5.QtCore import Qt

from exdrf_qt.models.record import (
    ERROR_BRUSH,
    ERROR_COLOR,
    LOADING_BRUSH,
    QtRecord,
)


class TestQtRecordInit(unittest.TestCase):
    """Test cases for QtRecord initialization."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_model = MagicMock(name="MockModel")
        self.mock_field1 = MagicMock(name="Field1")
        self.mock_field2 = MagicMock(name="Field2")
        self.mock_field3 = MagicMock(name="Field3")
        self.mock_model.column_fields = [
            self.mock_field1,
            self.mock_field2,
            self.mock_field3,
        ]
        self.mock_model.cache.index.return_value = 5
        self.mock_model.index.return_value = MagicMock(name="QModelIndex")
        self.mock_model.t = lambda key, default: default

    def test_init_with_db_id(self):
        """Test initialization with db_id sets loaded to True."""
        record = QtRecord(model=self.mock_model, db_id=123)

        self.assertEqual(record.db_id, 123)
        self.assertTrue(record.loaded)
        self.assertEqual(len(record.values), 3)
        for i in range(3):
            self.assertEqual(record.values[i], {})

    def test_init_with_none_db_id(self):
        """Test initialization with None db_id sets loaded to False."""
        record = QtRecord(model=self.mock_model, db_id=None)

        self.assertIsNone(record.db_id)
        self.assertFalse(record.loaded)
        self.assertEqual(len(record.values), 3)

    def test_init_with_minus_one_db_id(self):
        """Test initialization with -1 db_id sets loaded to False."""
        record = QtRecord(model=self.mock_model, db_id=-1)

        self.assertEqual(record.db_id, -1)
        self.assertFalse(record.loaded)


class TestQtRecordDisplayText(unittest.TestCase):
    """Test cases for display_text method."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_model = MagicMock(name="MockModel")
        self.mock_model.column_fields = [
            MagicMock(name="Field1"),
            MagicMock(name="Field2"),
        ]
        self.mock_model.cache.index.return_value = 0
        self.mock_model.index.return_value = MagicMock(name="QModelIndex")
        self.mock_model.t = lambda key, default: default

    def test_display_text_when_error(self):
        """Test display_text returns error message when error is True."""
        record = QtRecord(model=self.mock_model, db_id=1)
        record.error = True

        result = record.display_text()

        self.assertEqual(result, "Error")

    def test_display_text_when_not_loaded(self):
        """Test display_text returns loading message when not loaded."""
        record = QtRecord(model=self.mock_model, db_id=None)

        result = record.display_text()

        self.assertEqual(result, "Loading...")

    def test_display_text_when_loaded(self):
        """Test display_text returns comma-separated values when loaded."""
        record = QtRecord(model=self.mock_model, db_id=1)
        record.values[0][Qt.ItemDataRole.DisplayRole] = "Value1"
        record.values[1][Qt.ItemDataRole.DisplayRole] = "Value2"

        result = record.display_text()

        self.assertEqual(result, "Value1, Value2")

    def test_display_text_falls_back_to_edit_role(self):
        """Test display_text falls back to EditRole when DisplayRole missing."""
        record = QtRecord(model=self.mock_model, db_id=1)
        record.values[0][Qt.ItemDataRole.EditRole] = "EditValue"

        result = record.display_text()

        self.assertEqual(result, "EditValue, NULL")

    def test_display_text_falls_back_to_null(self):
        """Test display_text falls back to NULL when no role data."""
        record = QtRecord(model=self.mock_model, db_id=1)

        result = record.display_text()

        self.assertEqual(result, "NULL, NULL")


class TestQtRecordData(unittest.TestCase):
    """Test cases for data method."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_model = MagicMock(name="MockModel")
        self.mock_model.column_fields = [MagicMock(name="Field1")]
        self.mock_model.cache.index.return_value = 0
        self.mock_model.index.return_value = MagicMock(name="QModelIndex")
        self.mock_model.t = lambda key, default: default

    def test_data_when_error_background_color(self):
        """Test data returns ERROR_BRUSH when error and BackgroundColorRole."""
        record = QtRecord(model=self.mock_model, db_id=1)
        record.error = True

        result = record.data(0, Qt.ItemDataRole.BackgroundColorRole)

        self.assertEqual(result, ERROR_BRUSH)

    def test_data_when_not_loaded_background_color(self):
        """Test data returns LOADING_BRUSH when not loaded and BackgroundColorRole."""
        record = QtRecord(model=self.mock_model, db_id=None)

        result = record.data(0, Qt.ItemDataRole.BackgroundColorRole)

        self.assertEqual(result, LOADING_BRUSH)

    def test_data_when_error_foreground(self):
        """Test data returns ERROR_COLOR when error and ForegroundRole."""
        record = QtRecord(model=self.mock_model, db_id=1)
        record.error = True

        result = record.data(0, Qt.ItemDataRole.ForegroundRole)

        self.assertEqual(result, ERROR_COLOR)

    def test_data_when_error_display(self):
        """Test data returns 'error' when error and DisplayRole."""
        record = QtRecord(model=self.mock_model, db_id=1)
        record.error = True

        result = record.data(0, Qt.ItemDataRole.DisplayRole)

        self.assertEqual(result, "error")

    def test_data_when_not_loaded_display(self):
        """Test data returns ' ' when not loaded and DisplayRole."""
        record = QtRecord(model=self.mock_model, db_id=None)

        result = record.data(0, Qt.ItemDataRole.DisplayRole)

        self.assertEqual(result, " ")

    def test_data_when_error_edit_role(self):
        """Test data returns None when error and EditRole."""
        record = QtRecord(model=self.mock_model, db_id=1)
        record.error = True

        result = record.data(0, Qt.ItemDataRole.EditRole)

        self.assertIsNone(result)

    def test_data_when_error_text_alignment(self):
        """Test data returns center alignment when error and TextAlignmentRole."""
        record = QtRecord(model=self.mock_model, db_id=1)
        record.error = True

        result = record.data(0, Qt.ItemDataRole.TextAlignmentRole)

        expected = Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        self.assertEqual(result, expected)

    def test_data_when_loaded_returns_value(self):
        """Test data returns stored value when loaded."""
        record = QtRecord(model=self.mock_model, db_id=1)
        test_value = "Test Value"
        record.values[0][Qt.ItemDataRole.DisplayRole] = test_value

        result = record.data(0, Qt.ItemDataRole.DisplayRole)

        self.assertEqual(result, test_value)

    def test_data_when_column_not_found(self):
        """Test data returns None when column not in values."""
        record = QtRecord(model=self.mock_model, db_id=1)

        result = record.data(999, Qt.ItemDataRole.DisplayRole)

        self.assertIsNone(result)

    def test_data_when_role_not_found(self):
        """Test data returns None when role not in column data."""
        record = QtRecord(model=self.mock_model, db_id=1)
        record.values[0][Qt.ItemDataRole.DisplayRole] = "Value"

        result = record.data(0, Qt.ItemDataRole.EditRole)

        self.assertIsNone(result)


class TestQtRecordIndex(unittest.TestCase):
    """Test cases for index property."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_model = MagicMock(name="MockModel")
        self.mock_model.column_fields = [MagicMock(name="Field1")]
        self.mock_model.cache.index.return_value = 5
        self.mock_index = MagicMock(name="QModelIndex")
        self.mock_model.index.return_value = self.mock_index
        self.mock_model.t = lambda key, default: default

    def test_index_returns_model_index(self):
        """Test index property returns QModelIndex from model."""
        record = QtRecord(model=self.mock_model, db_id=1)

        result = record.index

        self.mock_model.cache.index.assert_called_once_with(record)
        self.mock_model.index.assert_called_once_with(5, 0)
        self.assertEqual(result, self.mock_index)


class TestQtRecordLoaded(unittest.TestCase):
    """Test cases for loaded property."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_model = MagicMock(name="MockModel")
        self.mock_model.column_fields = [
            MagicMock(name="Field1"),
            MagicMock(name="Field2"),
        ]
        self.mock_model.cache.index.return_value = 0
        self.mock_model.index.return_value = MagicMock(name="QModelIndex")
        self.mock_model.t = lambda key, default: default

    def test_loaded_getter_returns_value(self):
        """Test loaded getter returns _loaded value."""
        record = QtRecord(model=self.mock_model, db_id=1)

        self.assertTrue(record.loaded)

    def test_loaded_setter_to_false_sets_loading_brush(self):
        """Test setting loaded to False sets LOADING_BRUSH."""
        record = QtRecord(model=self.mock_model, db_id=1)

        record.loaded = False

        self.assertFalse(record.loaded)
        for i in range(2):
            self.assertEqual(
                record.values[i][Qt.ItemDataRole.BackgroundRole],
                LOADING_BRUSH,
            )

    def test_loaded_setter_to_true_does_not_set_brush(self):
        """Test setting loaded to True does not modify brushes."""
        record = QtRecord(model=self.mock_model, db_id=None)
        # Set some initial value
        record.values[0][Qt.ItemDataRole.BackgroundRole] = ERROR_BRUSH

        record.loaded = True

        self.assertTrue(record.loaded)
        # Should still have ERROR_BRUSH (not overwritten)
        self.assertEqual(
            record.values[0][Qt.ItemDataRole.BackgroundRole],
            ERROR_BRUSH,
        )


class TestQtRecordError(unittest.TestCase):
    """Test cases for error property."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_model = MagicMock(name="MockModel")
        self.mock_model.column_fields = [
            MagicMock(name="Field1"),
            MagicMock(name="Field2"),
        ]
        self.mock_model.cache.index.return_value = 0
        self.mock_model.index.return_value = MagicMock(name="QModelIndex")
        self.mock_model.t = lambda key, default: default

    def test_error_getter_returns_value(self):
        """Test error getter returns _error value."""
        record = QtRecord(model=self.mock_model, db_id=1)

        self.assertFalse(record.error)

    def test_error_setter_to_true_sets_error_brush(self):
        """Test setting error to True sets ERROR_BRUSH."""
        record = QtRecord(model=self.mock_model, db_id=1)

        record.error = True

        self.assertTrue(record.error)
        for i in range(2):
            self.assertEqual(
                record.values[i][Qt.ItemDataRole.BackgroundRole],
                ERROR_BRUSH,
            )

    def test_error_setter_to_false_does_not_modify_brush(self):
        """Test setting error to False does not modify brushes."""
        record = QtRecord(model=self.mock_model, db_id=1)
        record.error = True
        # Clear the brush to test
        del record.values[0][Qt.ItemDataRole.BackgroundRole]

        record.error = False

        self.assertFalse(record.error)
        # Should not have ERROR_BRUSH set
        self.assertNotIn(
            Qt.ItemDataRole.BackgroundRole,
            record.values[0],
        )


class TestQtRecordCellIndex(unittest.TestCase):
    """Test cases for cell_index method."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_model = MagicMock(name="MockModel")
        self.mock_model.column_fields = [MagicMock(name="Field1")]
        self.mock_model.cache.index.return_value = 7
        self.mock_index = MagicMock(name="QModelIndex")
        self.mock_model.index.return_value = self.mock_index
        self.mock_model.t = lambda key, default: default

    def test_cell_index_returns_model_index(self):
        """Test cell_index returns QModelIndex for specified column."""
        record = QtRecord(model=self.mock_model, db_id=1)

        result = record.cell_index(3)

        self.mock_model.cache.index.assert_called_once_with(record)
        self.mock_model.index.assert_called_once_with(7, 3)
        self.assertEqual(result, self.mock_index)


class TestQtRecordGetRowData(unittest.TestCase):
    """Test cases for get_row_data method."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_model = MagicMock(name="MockModel")
        self.mock_model.column_fields = [
            MagicMock(name="Field1"),
            MagicMock(name="Field2"),
            MagicMock(name="Field3"),
        ]
        self.mock_model.cache.index.return_value = 0
        self.mock_model.index.return_value = MagicMock(name="QModelIndex")
        self.mock_model.t = lambda key, default: default

    def test_get_row_data_returns_all_column_values(self):
        """Test get_row_data returns values for all columns."""
        record = QtRecord(model=self.mock_model, db_id=1)
        record.values[0][Qt.ItemDataRole.DisplayRole] = "Value1"
        record.values[1][Qt.ItemDataRole.DisplayRole] = "Value2"
        record.values[2][Qt.ItemDataRole.DisplayRole] = "Value3"

        result = record.get_row_data(Qt.ItemDataRole.DisplayRole)

        self.assertEqual(result, ["Value1", "Value2", "Value3"])

    def test_get_row_data_returns_none_for_missing_roles(self):
        """Test get_row_data returns None for columns without role data."""
        record = QtRecord(model=self.mock_model, db_id=1)
        record.values[0][Qt.ItemDataRole.DisplayRole] = "Value1"
        # Column 1 has no DisplayRole
        record.values[2][Qt.ItemDataRole.DisplayRole] = "Value3"

        result = record.get_row_data(Qt.ItemDataRole.DisplayRole)

        self.assertEqual(result, ["Value1", None, "Value3"])

    def test_get_row_data_returns_none_for_missing_columns(self):
        """Test get_row_data returns None for columns not in values dict."""
        record = QtRecord(model=self.mock_model, db_id=1)
        # Set value for column 0 and 2 (skip column 1)
        record.values[0][Qt.ItemDataRole.DisplayRole] = "Value1"
        record.values[2][Qt.ItemDataRole.DisplayRole] = "Value3"

        result = record.get_row_data(Qt.ItemDataRole.DisplayRole)

        # Should return list with None for column 1
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], "Value1")
        self.assertIsNone(result[1])
        self.assertEqual(result[2], "Value3")

    def test_get_row_data_with_different_role(self):
        """Test get_row_data works with different roles."""
        record = QtRecord(model=self.mock_model, db_id=1)
        record.values[0][Qt.ItemDataRole.EditRole] = "EditValue"

        result = record.get_row_data(Qt.ItemDataRole.EditRole)

        self.assertEqual(result[0], "EditValue")
        self.assertIsNone(result[1])
        self.assertIsNone(result[2])


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
