"""Tests for QtField in exdrf_qt.models.field."""

import unittest
from unittest.mock import MagicMock, patch

from exdrf.filter import FieldFilter
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QBrush, QColor, QFont

from exdrf_qt.models.field import (
    QtField,
    italic_font,
    light_grey,
    regular_font,
)


class TestQtFieldValues(unittest.TestCase):
    def test_values_raises_not_implemented(self) -> None:
        """Test that values method raises NotImplementedError."""
        field = QtField(ctx=None, resource=None)
        record = MagicMock()

        with self.assertRaises(NotImplementedError):
            field.values(record)


class TestQtFieldApplySorting(unittest.TestCase):
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_db_model = MagicMock()
        self.mock_column = MagicMock()
        self.mock_column.asc.return_value = "asc_result"
        self.mock_column.desc.return_value = "desc_result"
        self.mock_db_model.test_field = self.mock_column

        self.mock_resource = MagicMock()
        self.mock_resource.db_model = self.mock_db_model

        self.field = QtField(
            ctx=None, resource=self.mock_resource, name="test_field"
        )

    def test_apply_sorting_ascending(self) -> None:
        """Test apply_sorting with ascending=True."""
        result = self.field.apply_sorting(True)

        self.mock_column.asc.assert_called_once()
        self.assertEqual(result, "asc_result")

    def test_apply_sorting_descending(self) -> None:
        """Test apply_sorting with ascending=False."""
        result = self.field.apply_sorting(False)

        self.mock_column.desc.assert_called_once()
        self.assertEqual(result, "desc_result")


class TestQtFieldApplyFilter(unittest.TestCase):
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_db_model = MagicMock()
        self.mock_column = MagicMock()
        self.mock_db_model.test_field = self.mock_column

        self.mock_resource = MagicMock()
        self.mock_resource.db_model = self.mock_db_model

        self.mock_selector = MagicMock()

        self.mock_predicate = MagicMock(return_value="filter_result")
        self.mock_fi_op = MagicMock()
        self.mock_fi_op.predicate = self.mock_predicate

        self.field = QtField(
            ctx=None, resource=self.mock_resource, name="test_field"
        )

    def test_apply_filter_with_valid_operator(self) -> None:
        """Test apply_filter with a valid filter operator."""
        field_filter = FieldFilter(fld="test_field", op="eq", vl="test_value")

        with patch("exdrf_qt.models.field.filter_op_registry") as mock_registry:
            mock_registry.__getitem__.return_value = self.mock_fi_op
            result = self.field.apply_filter(field_filter, self.mock_selector)

            mock_registry.__getitem__.assert_called_once_with("eq")
            self.mock_predicate.assert_called_once_with(
                self.mock_column, "test_value"
            )
            self.assertEqual(result, "filter_result")

    def test_apply_filter_with_different_operator(self) -> None:
        """Test apply_filter with a different operator."""
        field_filter = FieldFilter(fld="test_field", op="ilike", vl="test%")

        with patch("exdrf_qt.models.field.filter_op_registry") as mock_registry:
            mock_registry.__getitem__.return_value = self.mock_fi_op
            self.field.apply_filter(field_filter, self.mock_selector)

            mock_registry.__getitem__.assert_called_once_with("ilike")
            self.mock_predicate.assert_called_once_with(
                self.mock_column, "test%"
            )


class TestQtFieldBlobValues(unittest.TestCase):
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.field = QtField(ctx=None, resource=None)

    def test_blob_values(self) -> None:
        """Test blob_values method."""
        blob_data = b"binary_data"

        result = self.field.blob_values(blob_data)

        self.assertEqual(result[Qt.ItemDataRole.EditRole], blob_data)
        self.assertEqual(result[Qt.ItemDataRole.DisplayRole], "BLOB")
        self.assertEqual(result[Qt.ItemDataRole.ToolTipRole], "BLOB")

    def test_blob_values_empty(self) -> None:
        """Test blob_values with empty bytes."""
        empty_blob = b""

        result = self.field.blob_values(empty_blob)

        self.assertEqual(result[Qt.ItemDataRole.EditRole], empty_blob)
        self.assertEqual(result[Qt.ItemDataRole.DisplayRole], "BLOB")


class TestQtFieldNotImplementedValues(unittest.TestCase):
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.field = QtField(ctx=None, resource=None)

    def test_not_implemented_values(self) -> None:
        """Test not_implemented_values method."""
        value = "some_value"

        result = self.field.not_implemented_values(value)

        self.assertEqual(result[Qt.ItemDataRole.EditRole], value)
        self.assertEqual(result[Qt.ItemDataRole.DisplayRole], "NOT IMPLEMENTED")
        self.assertEqual(result[Qt.ItemDataRole.ToolTipRole], "NOT IMPLEMENTED")

    def test_not_implemented_values_none(self) -> None:
        """Test not_implemented_values with None."""
        result = self.field.not_implemented_values(None)

        self.assertIsNone(result[Qt.ItemDataRole.EditRole])
        self.assertEqual(result[Qt.ItemDataRole.DisplayRole], "NOT IMPLEMENTED")


class TestQtFieldExpandValue(unittest.TestCase):
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.field = QtField(ctx=None, resource=None, preferred_width=150)

    def test_expand_value_with_string(self) -> None:
        """Test expand_value with a string value."""
        value = "test_string"

        result = self.field.expand_value(value)

        self.assertEqual(result[Qt.ItemDataRole.DisplayRole], value)
        self.assertEqual(result[Qt.ItemDataRole.EditRole], value)
        self.assertEqual(result[Qt.ItemDataRole.ToolTipRole], value)
        self.assertEqual(result[Qt.ItemDataRole.StatusTipRole], value)
        self.assertEqual(result[Qt.ItemDataRole.AccessibleTextRole], value)
        self.assertEqual(
            result[Qt.ItemDataRole.AccessibleDescriptionRole], value
        )
        self.assertIsNone(result[Qt.ItemDataRole.DecorationRole])
        self.assertIsNone(result[Qt.ItemDataRole.WhatsThisRole])
        self.assertIsNone(result[Qt.ItemDataRole.BackgroundRole])
        self.assertIsNone(result[Qt.ItemDataRole.ForegroundRole])
        self.assertIsNone(result[Qt.ItemDataRole.CheckStateRole])
        self.assertEqual(result[Qt.ItemDataRole.FontRole], regular_font)
        self.assertEqual(
            result[Qt.ItemDataRole.TextAlignmentRole],
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        self.assertEqual(
            result[Qt.ItemDataRole.SizeHintRole],
            QSize(self.field.preferred_width, 24),
        )

    def test_expand_value_with_none(self) -> None:
        """Test expand_value with None value."""
        with patch.object(self.field, "t") as mock_t:
            mock_t.return_value = "NULL"
            mock_t.side_effect = lambda key, default: (
                "NULL" if "null" in key else default
            )

            result = self.field.expand_value(None)

            self.assertEqual(result[Qt.ItemDataRole.DisplayRole], "NULL")
            self.assertEqual(result[Qt.ItemDataRole.FontRole], italic_font)
            self.assertEqual(result[Qt.ItemDataRole.ForegroundRole], light_grey)
            self.assertEqual(result[Qt.ItemDataRole.AccessibleTextRole], "NULL")
            self.assertEqual(
                result[Qt.ItemDataRole.TextAlignmentRole],
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
            )
            self.assertEqual(
                result[Qt.ItemDataRole.SizeHintRole], QSize(24, 24)
            )

    def test_expand_value_with_kwargs_override(self) -> None:
        """Test expand_value with kwargs to override default roles."""
        value = "test"
        custom_font = QFont("Times", 12)
        custom_color = QBrush(QColor(255, 0, 0))

        result = self.field.expand_value(
            value, FontRole=custom_font, BackgroundRole=custom_color
        )

        self.assertEqual(result[Qt.ItemDataRole.FontRole], custom_font)
        self.assertEqual(result[Qt.ItemDataRole.BackgroundRole], custom_color)
        self.assertEqual(result[Qt.ItemDataRole.DisplayRole], value)

    def test_expand_value_with_integer(self) -> None:
        """Test expand_value with an integer value."""
        value = 42

        result = self.field.expand_value(value)

        self.assertEqual(result[Qt.ItemDataRole.DisplayRole], value)
        self.assertEqual(result[Qt.ItemDataRole.EditRole], value)

    def test_expand_value_with_empty_string(self) -> None:
        """Test expand_value with an empty string."""
        value = ""

        result = self.field.expand_value(value)

        self.assertEqual(result[Qt.ItemDataRole.DisplayRole], "")
        self.assertEqual(result[Qt.ItemDataRole.EditRole], "")

    def test_expand_value_custom_preferred_width(self) -> None:
        """Test expand_value uses custom preferred_width."""
        field = QtField(ctx=None, resource=None, preferred_width=200)
        value = "test"

        result = field.expand_value(value)

        self.assertEqual(result[Qt.ItemDataRole.SizeHintRole], QSize(200, 24))


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
