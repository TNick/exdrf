"""Tests for exdrf_qt.models.field_list module."""

import unittest
from unittest.mock import MagicMock

from exdrf_qt.models.field_list import FieldsList


class MockQtField:
    """Mock QtField for testing."""

    def __init__(
        self,
        name: str,
        qsearch: bool = False,
        filterable: bool = False,
        sortable: bool = False,
        visible: bool = False,
        exportable: bool = False,
    ):
        """Initialize a mock field."""
        self.name = name
        self.qsearch = qsearch
        self.filterable = filterable
        self.sortable = sortable
        self.visible = visible
        self.exportable = exportable


class TestFieldsListFieldsProperty(unittest.TestCase):
    """Test cases for fields property."""

    def setUp(self):
        """Set up test fixtures."""
        self.fields_list = FieldsList()
        self.field1 = MockQtField("field1")
        self.field2 = MockQtField("field2")
        self.field3 = MockQtField("field3")

    def test_fields_getter_raises_attribute_error_when_not_set(self):
        """Test fields getter raises AttributeError when _fields not set."""
        fields_list = FieldsList()
        # Accessing fields before setting should raise AttributeError
        with self.assertRaises(AttributeError):
            _ = fields_list.fields

    def test_fields_getter_returns_list_after_setter(self):
        """Test fields getter returns list of fields after setter."""
        self.fields_list.fields = [self.field1, self.field2, self.field3]

        result = self.fields_list.fields

        self.assertEqual(len(result), 3)
        self.assertIn(self.field1, result)
        self.assertIn(self.field2, result)
        self.assertIn(self.field3, result)

    def test_fields_setter_creates_ordered_dict(self):
        """Test fields setter creates ordered dictionary."""
        self.fields_list.fields = [self.field1, self.field2, self.field3]

        self.assertEqual(len(self.fields_list._fields), 3)
        self.assertEqual(self.fields_list._fields["field1"], self.field1)
        self.assertEqual(self.fields_list._fields["field2"], self.field2)
        self.assertEqual(self.fields_list._fields["field3"], self.field3)

    def test_fields_setter_categorizes_fields(self):
        """Test fields setter categorizes fields correctly."""
        field_qsearch = MockQtField("qsearch_field", qsearch=True)
        field_filterable = MockQtField("filterable_field", filterable=True)
        field_sortable = MockQtField("sortable_field", sortable=True)
        field_visible = MockQtField("visible_field", visible=True)
        field_exportable = MockQtField("exportable_field", exportable=True)
        field_all = MockQtField(
            "all_field",
            qsearch=True,
            filterable=True,
            sortable=True,
            visible=True,
            exportable=True,
        )

        self.fields_list.fields = [
            field_qsearch,
            field_filterable,
            field_sortable,
            field_visible,
            field_exportable,
            field_all,
        ]

        self.assertIn(field_qsearch, self.fields_list._s_s_fields)
        self.assertIn(field_filterable, self.fields_list._f_fields)
        self.assertIn(field_sortable, self.fields_list._s_fields)
        self.assertIn(field_visible, self.fields_list._c_fields)
        self.assertIn(field_exportable, self.fields_list._e_fields)

        # field_all should be in all categories
        self.assertIn(field_all, self.fields_list._s_s_fields)
        self.assertIn(field_all, self.fields_list._f_fields)
        self.assertIn(field_all, self.fields_list._s_fields)
        self.assertIn(field_all, self.fields_list._c_fields)
        self.assertIn(field_all, self.fields_list._e_fields)

    def test_fields_setter_with_type_instantiates(self):
        """Test fields setter instantiates field classes."""
        mock_field_class = MagicMock()
        mock_field_class.return_value = self.field1
        mock_field_class.name = "field1"

        # Mock ctx and resource on fields_list
        self.fields_list.ctx = MagicMock()
        self.fields_list.resource = MagicMock()

        self.fields_list.fields = [mock_field_class]

        # Verify the field was instantiated
        mock_field_class.assert_called_once_with(
            ctx=self.fields_list.ctx, resource=self.fields_list.resource
        )

    def test_fields_setter_with_callable_instantiates(self):
        """Test fields setter instantiates callable field factories."""
        mock_callable_field = MagicMock()
        mock_callable_field.return_value = self.field1
        self.field1.name = "field1"

        # Mock ctx and resource on fields_list
        self.fields_list.ctx = MagicMock()
        self.fields_list.resource = MagicMock()

        self.fields_list.fields = [mock_callable_field]

        # Verify the field was instantiated
        mock_callable_field.assert_called_once_with(
            ctx=self.fields_list.ctx, resource=self.fields_list.resource
        )


class TestFieldsListGetField(unittest.TestCase):
    """Test cases for get_field method."""

    def setUp(self):
        """Set up test fixtures."""
        self.fields_list = FieldsList()
        self.field1 = MockQtField("field1")
        self.field2 = MockQtField("field2")
        self.fields_list.fields = [self.field1, self.field2]

    def test_get_field_with_raise_e_true_returns_field(self):
        """Test get_field with raise_e=True returns field."""
        result = self.fields_list.get_field("field1", raise_e=True)

        self.assertEqual(result, self.field1)

    def test_get_field_with_raise_e_true_raises_keyerror(self):
        """Test get_field with raise_e=True raises KeyError if not found."""
        with self.assertRaises(KeyError):
            self.fields_list.get_field("nonexistent", raise_e=True)

    def test_get_field_with_raise_e_false_returns_field(self):
        """Test get_field with raise_e=False returns field."""
        result = self.fields_list.get_field("field2", raise_e=False)

        self.assertEqual(result, self.field2)

    def test_get_field_with_raise_e_false_returns_none(self):
        """Test get_field with raise_e=False returns None if not found."""
        result = self.fields_list.get_field("nonexistent", raise_e=False)

        self.assertIsNone(result)

    def test_get_field_default_raise_e_raises(self):
        """Test get_field defaults to raise_e=True."""
        with self.assertRaises(KeyError):
            self.fields_list.get_field("nonexistent")


class TestFieldsListSimpleSearchFields(unittest.TestCase):
    """Test cases for simple_search_fields property."""

    def setUp(self):
        """Set up test fixtures."""
        self.fields_list = FieldsList()
        self.field1 = MockQtField("field1", qsearch=True)
        self.field2 = MockQtField("field2", qsearch=True)
        self.field3 = MockQtField("field3", qsearch=False)
        self.fields_list.fields = [self.field1, self.field2, self.field3]

    def test_simple_search_fields_getter(self):
        """Test simple_search_fields getter returns correct fields."""
        result = self.fields_list.simple_search_fields

        self.assertEqual(len(result), 2)
        self.assertIn(self.field1, result)
        self.assertIn(self.field2, result)
        self.assertNotIn(self.field3, result)

    def test_simple_search_fields_setter(self):
        """Test simple_search_fields setter sets fields by name."""
        self.fields_list.simple_search_fields = ["field1", "field3"]

        result = self.fields_list.simple_search_fields
        self.assertEqual(len(result), 2)
        self.assertIn(self.field1, result)
        self.assertIn(self.field3, result)

    def test_remove_from_ssf(self):
        """Test remove_from_ssf removes field from list."""
        result = self.fields_list.remove_from_ssf("field1")

        self.assertNotIn(self.field1, result)
        self.assertIn(self.field2, result)
        self.assertEqual(result, self.fields_list._s_s_fields)

    def test_remove_from_ssf_nonexistent(self):
        """Test remove_from_ssf handles nonexistent field."""
        original_length = len(self.fields_list._s_s_fields)
        result = self.fields_list.remove_from_ssf("nonexistent")

        self.assertEqual(len(result), original_length)


class TestFieldsListFilterFields(unittest.TestCase):
    """Test cases for filter_fields property."""

    def setUp(self):
        """Set up test fixtures."""
        self.fields_list = FieldsList()
        self.field1 = MockQtField("field1", filterable=True)
        self.field2 = MockQtField("field2", filterable=True)
        self.field3 = MockQtField("field3", filterable=False)
        self.fields_list.fields = [self.field1, self.field2, self.field3]

    def test_filter_fields_getter(self):
        """Test filter_fields getter returns correct fields."""
        result = self.fields_list.filter_fields

        self.assertEqual(len(result), 2)
        self.assertIn(self.field1, result)
        self.assertIn(self.field2, result)
        self.assertNotIn(self.field3, result)

    def test_filter_fields_setter(self):
        """Test filter_fields setter sets fields by name."""
        self.fields_list.filter_fields = ["field1", "field3"]

        result = self.fields_list.filter_fields
        self.assertEqual(len(result), 2)
        self.assertIn(self.field1, result)
        self.assertIn(self.field3, result)

    def test_remove_from_ff(self):
        """Test remove_from_ff removes field from list."""
        result = self.fields_list.remove_from_ff("field1")

        self.assertNotIn(self.field1, result)
        self.assertIn(self.field2, result)
        self.assertEqual(result, self.fields_list._f_fields)

    def test_remove_from_ff_nonexistent(self):
        """Test remove_from_ff handles nonexistent field."""
        original_length = len(self.fields_list._f_fields)
        result = self.fields_list.remove_from_ff("nonexistent")

        self.assertEqual(len(result), original_length)


class TestFieldsListSortableFields(unittest.TestCase):
    """Test cases for sortable_fields property."""

    def setUp(self):
        """Set up test fixtures."""
        self.fields_list = FieldsList()
        self.field1 = MockQtField("field1", sortable=True)
        self.field2 = MockQtField("field2", sortable=True)
        self.field3 = MockQtField("field3", sortable=False)
        self.fields_list.fields = [self.field1, self.field2, self.field3]

    def test_sortable_fields_getter(self):
        """Test sortable_fields getter returns correct fields."""
        result = self.fields_list.sortable_fields

        self.assertEqual(len(result), 2)
        self.assertIn(self.field1, result)
        self.assertIn(self.field2, result)
        self.assertNotIn(self.field3, result)

    def test_sortable_fields_setter(self):
        """Test sortable_fields setter sets fields by name."""
        self.fields_list.sortable_fields = ["field1", "field3"]

        result = self.fields_list.sortable_fields
        self.assertEqual(len(result), 2)
        self.assertIn(self.field1, result)
        self.assertIn(self.field3, result)

    def test_remove_from_sf(self):
        """Test remove_from_sf removes field from list."""
        result = self.fields_list.remove_from_sf("field1")

        self.assertNotIn(self.field1, result)
        self.assertIn(self.field2, result)
        self.assertEqual(result, self.fields_list._s_fields)

    def test_remove_from_sf_nonexistent(self):
        """Test remove_from_sf handles nonexistent field."""
        original_length = len(self.fields_list._s_fields)
        result = self.fields_list.remove_from_sf("nonexistent")

        self.assertEqual(len(result), original_length)


class TestFieldsListColumnFields(unittest.TestCase):
    """Test cases for column_fields property."""

    def setUp(self):
        """Set up test fixtures."""
        self.fields_list = FieldsList()
        self.field1 = MockQtField("field1", visible=True)
        self.field2 = MockQtField("field2", visible=True)
        self.field3 = MockQtField("field3", visible=False)
        self.fields_list.fields = [self.field1, self.field2, self.field3]

    def test_column_fields_getter(self):
        """Test column_fields getter returns correct fields."""
        result = self.fields_list.column_fields

        self.assertEqual(len(result), 2)
        self.assertIn(self.field1, result)
        self.assertIn(self.field2, result)
        self.assertNotIn(self.field3, result)

    def test_column_fields_setter(self):
        """Test column_fields setter sets fields by name."""
        self.fields_list.column_fields = ["field1", "field3"]

        result = self.fields_list.column_fields
        self.assertEqual(len(result), 2)
        self.assertIn(self.field1, result)
        self.assertIn(self.field3, result)

    def test_remove_from_cf(self):
        """Test remove_from_cf removes field from list."""
        result = self.fields_list.remove_from_cf("field1")

        self.assertNotIn(self.field1, result)
        self.assertIn(self.field2, result)
        self.assertEqual(result, self.fields_list._c_fields)

    def test_remove_from_cf_nonexistent(self):
        """Test remove_from_cf handles nonexistent field."""
        original_length = len(self.fields_list._c_fields)
        result = self.fields_list.remove_from_cf("nonexistent")

        self.assertEqual(len(result), original_length)


class TestFieldsListExportableFields(unittest.TestCase):
    """Test cases for exportable_fields property."""

    def setUp(self):
        """Set up test fixtures."""
        self.fields_list = FieldsList()
        self.field1 = MockQtField("field1", exportable=True)
        self.field2 = MockQtField("field2", exportable=True)
        self.field3 = MockQtField("field3", exportable=False)
        self.fields_list.fields = [self.field1, self.field2, self.field3]

    def test_exportable_fields_getter(self):
        """Test exportable_fields getter returns correct fields."""
        result = self.fields_list.exportable_fields

        self.assertEqual(len(result), 2)
        self.assertIn(self.field1, result)
        self.assertIn(self.field2, result)
        self.assertNotIn(self.field3, result)

    def test_exportable_fields_setter(self):
        """Test exportable_fields setter sets fields by name."""
        self.fields_list.exportable_fields = ["field1", "field3"]

        result = self.fields_list.exportable_fields
        self.assertEqual(len(result), 2)
        self.assertIn(self.field1, result)
        self.assertIn(self.field3, result)

    def test_remove_from_ef(self):
        """Test remove_from_ef removes field from list."""
        result = self.fields_list.remove_from_ef("field1")

        self.assertNotIn(self.field1, result)
        self.assertIn(self.field2, result)
        self.assertEqual(result, self.fields_list._e_fields)

    def test_remove_from_ef_nonexistent(self):
        """Test remove_from_ef handles nonexistent field."""
        original_length = len(self.fields_list._e_fields)
        result = self.fields_list.remove_from_ef("nonexistent")

        self.assertEqual(len(result), original_length)


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
