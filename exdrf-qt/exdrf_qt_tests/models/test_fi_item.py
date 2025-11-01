"""Tests for exdrf_qt.models.fi_item module."""

import unittest
from unittest.mock import MagicMock

from exdrf_qt.models.fi_item import SqBaseFiItem, SqFiItem


class TestSqBaseFiItem(unittest.TestCase):
    """Test cases for SqBaseFiItem class."""

    def test_apply_raises_not_implemented_error(self):
        """Test that apply raises NotImplementedError on base class."""
        item = SqBaseFiItem()

        with self.assertRaises(NotImplementedError):
            mock_selection = MagicMock(name="MockSelect")
            item.apply(mock_selection)


class TestSqFiItem(unittest.TestCase):
    """Test cases for SqFiItem class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_field = MagicMock(name="MockField")
        self.mock_op = MagicMock(name="MockOp")
        self.mock_value = MagicMock(name="MockValue")
        self.mock_selection = MagicMock(name="MockSelection")
        self.mock_result_selection = MagicMock(name="MockResultSelection")

        # Configure mock_op.apply_filter to return a result
        self.mock_op.apply_filter.return_value = self.mock_result_selection

        self.fi_item = SqFiItem(
            field=self.mock_field, op=self.mock_op, value=self.mock_value
        )

    def test_apply_calls_op_apply_filter_with_correct_parameters(self):
        """Test that apply calls op.apply_filter with correct parameters."""
        result = self.fi_item.apply(self.mock_selection)

        self.mock_op.apply_filter.assert_called_once_with(
            selector=self.mock_field,
            value=self.mock_value,
            selection=self.mock_selection,
            item=self.fi_item,
        )
        self.assertEqual(result, self.mock_result_selection)

    def test_apply_returns_result_from_op_apply_filter(self):
        """Test that apply returns the result from op.apply_filter."""
        mock_new_result = MagicMock(name="NewResult")
        self.mock_op.apply_filter.return_value = mock_new_result

        result = self.fi_item.apply(self.mock_selection)

        self.assertEqual(result, mock_new_result)

    def test_fi_item_attributes(self):
        """Test that FiItem has correct attributes."""
        self.assertEqual(self.fi_item.field, self.mock_field)
        self.assertEqual(self.fi_item.op, self.mock_op)
        self.assertEqual(self.fi_item.value, self.mock_value)

    def test_fi_item_inherits_from_base(self):
        """Test that SqFiItem inherits from SqBaseFiItem."""
        self.assertIsInstance(self.fi_item, SqBaseFiItem)


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
