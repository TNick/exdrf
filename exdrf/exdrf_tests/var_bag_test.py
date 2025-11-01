from datetime import date, datetime

import pytest

from exdrf.constants import FIELD_TYPE_STRING
from exdrf.field_types.api import DateTimeField, StrField
from exdrf.var_bag import VarBag


@pytest.fixture
def empty_var_bag():
    """Create an empty VarBag."""
    return VarBag()


@pytest.fixture
def sample_field():
    """Create a sample StrField."""
    return StrField(name="test_field")


@pytest.fixture
def sample_var_bag(sample_field):
    """Create a VarBag with one field."""
    bag = VarBag()
    bag.add_field(sample_field, "test_value")
    return bag


class TestVarBagInitialization:
    """Tests for VarBag initialization."""

    def test_empty_initialization(self, empty_var_bag):
        """Test that VarBag can be initialized empty."""
        assert len(empty_var_bag) == 0
        assert empty_var_bag.values == {}
        assert empty_var_bag._fields == {}
        assert list(empty_var_bag) == []

    def test_initialization_with_values(self):
        """Test that VarBag can be initialized with values."""
        bag = VarBag(values={"key1": "value1", "key2": 42})
        assert len(bag) == 2
        assert "key1" in bag
        assert "key2" in bag


class TestVarBagProperties:
    """Tests for VarBag properties."""

    def test_var_names(self, sample_var_bag):
        """Test var_names property."""
        assert sample_var_bag.var_names == ["test_field"]

    def test_var_names_empty(self, empty_var_bag):
        """Test var_names on empty bag."""
        assert empty_var_bag.var_names == []

    def test_var_names_multiple(self):
        """Test var_names with multiple fields."""
        bag = VarBag()
        bag.values["field1"] = "value1"
        bag.values["field2"] = "value2"
        assert set(bag.var_names) == {"field1", "field2"}

    def test_var_values(self, sample_var_bag):
        """Test var_values property."""
        assert sample_var_bag.var_values == ["test_value"]

    def test_var_values_empty(self, empty_var_bag):
        """Test var_values on empty bag."""
        assert empty_var_bag.var_values == []

    def test_field_names(self, sample_var_bag):
        """Test field_names property."""
        assert sample_var_bag.field_names == ["test_field"]

    def test_field_names_empty(self, empty_var_bag):
        """Test field_names on empty bag."""
        assert empty_var_bag.field_names == []

    def test_field_values(self, sample_var_bag):
        """Test field_values property."""
        assert sample_var_bag.field_values == ["test_value"]

    def test_field_values_empty(self, empty_var_bag):
        """Test field_values on empty bag."""
        assert empty_var_bag.field_values == []

    def test_field_count(self, sample_var_bag):
        """Test field_count property."""
        assert sample_var_bag.field_count == 1

    def test_field_count_empty(self, empty_var_bag):
        """Test field_count on empty bag."""
        assert empty_var_bag.field_count == 0

    def test_field_count_multiple(self):
        """Test field_count with multiple fields."""
        bag = VarBag()
        bag.values["field1"] = "value1"
        bag.values["field2"] = "value2"
        assert bag.field_count == 2

    def test_as_field_dict(self, sample_var_bag):
        """Test as_field_dict property."""
        assert sample_var_bag.as_field_dict == {"test_field": "test_value"}

    def test_as_field_dict_empty(self, empty_var_bag):
        """Test as_field_dict on empty bag."""
        assert empty_var_bag.as_field_dict == {}

    def test_fields_property(self, sample_var_bag, sample_field):
        """Test fields property."""
        fields = sample_var_bag.fields
        assert len(fields) == 1
        assert fields[0].name == "test_field"

    def test_fields_property_without_field_object(self):
        """Test fields property when value exists but no field object."""
        bag = VarBag()
        bag.values["raw_value"] = "some_value"
        assert len(bag.fields) == 0

    def test_as_dict(self, sample_var_bag):
        """Test as_dict property."""
        assert sample_var_bag.as_dict == {"test_field": "test_value"}


class TestVarBagAddField:
    """Tests for add_field method."""

    def test_add_field(self, empty_var_bag, sample_field):
        """Test adding a single field."""
        empty_var_bag.add_field(sample_field, "test_value")
        assert "test_field" in empty_var_bag
        assert empty_var_bag["test_field"] == "test_value"
        assert empty_var_bag._fields["test_field"] == sample_field

    def test_add_field_updates_existing(self, sample_var_bag):
        """Test that add_field updates existing field."""
        new_field = StrField(name="test_field")
        sample_var_bag.add_field(new_field, "new_value")
        assert sample_var_bag["test_field"] == "new_value"
        assert sample_var_bag._fields["test_field"] == new_field

    def test_add_field_with_none_value(self, empty_var_bag, sample_field):
        """Test adding a field with None value."""
        empty_var_bag.add_field(sample_field, None)
        assert "test_field" in empty_var_bag
        assert empty_var_bag["test_field"] is None


class TestVarBagAddFields:
    """Tests for add_fields method."""

    def test_add_fields(self, empty_var_bag):
        """Test adding multiple fields."""
        field1 = StrField(name="field1")
        field2 = StrField(name="field2")
        empty_var_bag.add_fields([(field1, "value1"), (field2, "value2")])
        assert "field1" in empty_var_bag
        assert "field2" in empty_var_bag
        assert empty_var_bag["field1"] == "value1"
        assert empty_var_bag["field2"] == "value2"

    def test_add_fields_updates_existing(self, sample_var_bag):
        """Test that add_fields updates existing fields."""
        new_field = StrField(name="test_field")
        field2 = StrField(name="field2")
        sample_var_bag.add_fields([(new_field, "updated"), (field2, "value2")])
        assert sample_var_bag["test_field"] == "updated"
        assert sample_var_bag["field2"] == "value2"


class TestVarBagContainsField:
    """Tests for contains_field method."""

    def test_contains_field_true(self, sample_var_bag):
        """Test contains_field returns True for existing field."""
        assert sample_var_bag.contains_field("test_field") is True

    def test_contains_field_false(self, empty_var_bag):
        """Test contains_field returns False for non-existing field."""
        assert empty_var_bag.contains_field("nonexistent") is False

    def test_contains_field_with_raw_value(self):
        """Test contains_field with raw value (no field object)."""
        bag = VarBag()
        bag.values["raw_value"] = "some_value"
        assert bag.contains_field("raw_value") is True


class TestVarBagIsField:
    """Tests for is_field method."""

    def test_is_field_true(self, sample_var_bag):
        """Test is_field returns True when field object exists."""
        assert sample_var_bag.is_field("test_field") is True

    def test_is_field_false(self, empty_var_bag):
        """Test is_field returns False for non-existing field."""
        assert empty_var_bag.is_field("nonexistent") is False

    def test_is_field_false_with_raw_value(self):
        """Test is_field returns False for raw value without field object."""
        bag = VarBag()
        bag.values["raw_value"] = "some_value"
        assert bag.is_field("raw_value") is False


class TestVarBagGetFieldValue:
    """Tests for get_field_value method."""

    def test_get_field_value(self, sample_var_bag):
        """Test getting field value."""
        assert sample_var_bag.get_field_value("test_field") == "test_value"

    def test_get_field_value_raises_keyerror(self, empty_var_bag):
        """Test get_field_value raises KeyError for non-existing field."""
        with pytest.raises(KeyError, match="Key nonexistent not found"):
            empty_var_bag.get_field_value("nonexistent")


class TestVarBagSetFieldValue:
    """Tests for set_field_value method."""

    def test_set_field_value(self, sample_var_bag):
        """Test setting field value."""
        sample_var_bag.set_field_value("test_field", "new_value")
        assert sample_var_bag["test_field"] == "new_value"

    def test_set_field_value_raises_keyerror(self, empty_var_bag):
        """Test set_field_value raises KeyError for non-existing field."""
        with pytest.raises(KeyError, match="Key nonexistent not found"):
            empty_var_bag.set_field_value("nonexistent", "value")


class TestVarBagMagicMethods:
    """Tests for magic methods."""

    def test_contains(self, sample_var_bag):
        """Test __contains__ method."""
        assert "test_field" in sample_var_bag
        assert "nonexistent" not in sample_var_bag

    def test_getitem(self, sample_var_bag):
        """Test __getitem__ method."""
        assert sample_var_bag["test_field"] == "test_value"

    def test_getitem_raises_keyerror(self, empty_var_bag):
        """Test __getitem__ raises KeyError for non-existing key."""
        with pytest.raises(KeyError, match="Key nonexistent not found"):
            _ = empty_var_bag["nonexistent"]

    def test_setitem(self, sample_var_bag):
        """Test __setitem__ method."""
        sample_var_bag["test_field"] = "updated_value"
        assert sample_var_bag["test_field"] == "updated_value"

    def test_setitem_raises_keyerror(self, empty_var_bag):
        """Test __setitem__ raises KeyError for non-existing key."""
        with pytest.raises(KeyError, match="Key nonexistent not found"):
            empty_var_bag["nonexistent"] = "value"

    def test_iter(self, sample_var_bag):
        """Test __iter__ method."""
        keys = list(sample_var_bag)
        assert keys == ["test_field"]

    def test_iter_empty(self, empty_var_bag):
        """Test __iter__ on empty bag."""
        assert list(empty_var_bag) == []

    def test_len(self, sample_var_bag):
        """Test __len__ method."""
        assert len(sample_var_bag) == 1

    def test_len_empty(self, empty_var_bag):
        """Test __len__ on empty bag."""
        assert len(empty_var_bag) == 0


class TestVarBagFiltered:
    """Tests for filtered method."""

    def test_filtered_empty_text(self, sample_var_bag):
        """Test filtered with empty text returns same bag."""
        result = sample_var_bag.filtered(True, "", False)
        assert result.values == sample_var_bag.values
        assert result._fields == sample_var_bag._fields

    def test_filtered_by_name_exact(self, sample_var_bag):
        """Test filtered by name with exact match."""
        field2 = StrField(name="another_field")
        sample_var_bag.add_field(field2, "value2")
        result = sample_var_bag.filtered(True, "test_field", True)
        assert "test_field" in result
        assert "another_field" not in result

    def test_filtered_by_name_pattern(self):
        """Test filtered by name with pattern matching."""
        bag = VarBag()
        bag.values["field1"] = "value1"
        bag.values["field2"] = "value2"
        bag.values["other"] = "value3"
        result = bag.filtered(True, "field*", False)
        assert "field1" in result
        assert "field2" in result
        assert "other" not in result

    def test_filtered_by_value(self):
        """Test filtered by value."""
        bag = VarBag()
        bag.values["field1"] = "hello world"
        bag.values["field2"] = "goodbye"
        result = bag.filtered(False, "hello", False)
        assert "field1" in result
        assert "field2" not in result

    def test_filtered_preserves_field_objects(self):
        """Test that filtered preserves field objects."""
        bag = VarBag()
        field1 = StrField(name="field1")
        bag.add_field(field1, "value1")
        bag.values["field2"] = "value2"  # Raw value without field object
        result = bag.filtered(True, "field*", False)
        assert "field1" in result._fields
        assert "field2" not in result._fields


class TestVarBagFilteredFields:
    """Tests for filtered_fields method."""

    def test_filtered_fields(self):
        """Test filtered_fields method."""
        bag = VarBag()
        bag.values["field1"] = "value1"
        bag.values["field2"] = "value2"
        result = bag.filtered_fields(True, "field1", True)
        assert "field1" in result
        assert "field2" not in result


class TestVarBagAddNow:
    """Tests for add_now method."""

    def test_add_now(self, empty_var_bag):
        """Test add_now adds current datetime."""
        empty_var_bag.add_now()
        assert "now" in empty_var_bag
        assert isinstance(empty_var_bag["now"], datetime)
        assert isinstance(empty_var_bag._fields["now"], DateTimeField)


class TestVarBagSimplifyValue:
    """Tests for simplify_value method."""

    def test_simplify_value_str(self, empty_var_bag):
        """Test simplifying string value."""
        assert empty_var_bag.simplify_value("test") == "test"

    def test_simplify_value_int(self, empty_var_bag):
        """Test simplifying int value."""
        assert empty_var_bag.simplify_value(42) == 42

    def test_simplify_value_float(self, empty_var_bag):
        """Test simplifying float value."""
        assert empty_var_bag.simplify_value(3.14) == 3.14

    def test_simplify_value_bool(self, empty_var_bag):
        """Test simplifying bool value."""
        assert empty_var_bag.simplify_value(True) is True

    def test_simplify_value_datetime(self, empty_var_bag):
        """Test simplifying datetime value."""
        dt = datetime(2023, 1, 1, 12, 30, 45)
        assert empty_var_bag.simplify_value(dt) == "2023-01-01T12:30:45"

    def test_simplify_value_date(self, empty_var_bag):
        """Test simplifying date value."""
        d = date(2023, 1, 1)
        assert empty_var_bag.simplify_value(d) == "2023-01-01"

    def test_simplify_value_list(self, empty_var_bag):
        """Test simplifying list value."""
        result = empty_var_bag.simplify_value([1, 2, 3])
        assert result == [1, 2, 3]

    def test_simplify_value_dict(self, empty_var_bag):
        """Test simplifying dict value."""
        result = empty_var_bag.simplify_value({"key": "value"})
        assert result == {"key": "value"}

    def test_simplify_value_nested_list(self, empty_var_bag):
        """Test simplifying nested list."""
        dt = datetime(2023, 1, 1, 12, 0, 0)
        result = empty_var_bag.simplify_value([dt, "test"])
        assert result == ["2023-01-01T12:00:00", "test"]

    def test_simplify_value_nested_dict(self, empty_var_bag):
        """Test simplifying nested dict."""
        dt = datetime(2023, 1, 1, 12, 0, 0)
        result = empty_var_bag.simplify_value({"time": dt})
        assert result == {"time": "2023-01-01T12:00:00"}

    def test_simplify_value_custom_class(self, empty_var_bag):
        """Test simplifying custom class."""

        class CustomClass:
            pass

        result = empty_var_bag.simplify_value(CustomClass())
        assert result == "<CustomClass>"


class TestVarBagToSimpleData:
    """Tests for to_simple_data method."""

    def test_to_simple_data_with_field(self, sample_var_bag):
        """Test to_simple_data with field object."""
        data = sample_var_bag.to_simple_data()
        assert len(data) == 1
        assert data[0]["name"] == "test_field"
        assert data[0]["type"] == FIELD_TYPE_STRING
        assert data[0]["value"] == "test_value"

    def test_to_simple_data_without_field(self):
        """Test to_simple_data without field object."""
        bag = VarBag()
        bag.values["raw_value"] = "some_value"
        data = bag.to_simple_data()
        assert len(data) == 1
        assert data[0]["name"] == "raw_value"
        assert data[0]["type"] == FIELD_TYPE_STRING
        assert data[0]["value"] == "some_value"

    def test_to_simple_data_empty(self, empty_var_bag):
        """Test to_simple_data on empty bag."""
        assert empty_var_bag.to_simple_data() == []

    def test_to_simple_data_with_datetime(self):
        """Test to_simple_data with datetime value."""
        bag = VarBag()
        field = DateTimeField(name="dt_field")
        dt = datetime(2023, 1, 1, 12, 30, 45)
        bag.add_field(field, dt)
        data = bag.to_simple_data()
        assert data[0]["value"] == "2023-01-01T12:30:45"


class TestVarBagFromSimpleData:
    """Tests for from_simple_data method."""

    def test_from_simple_data(self, empty_var_bag):
        """Test from_simple_data with valid data."""
        data = [
            {"name": "field1", "type": FIELD_TYPE_STRING, "value": "value1"},
            {"name": "field2", "type": FIELD_TYPE_STRING, "value": "value2"},
        ]
        empty_var_bag.from_simple_data(data)
        assert "field1" in empty_var_bag
        assert "field2" in empty_var_bag
        assert empty_var_bag["field1"] == "value1"
        assert empty_var_bag["field2"] == "value2"

    def test_from_simple_data_skips_empty_name(self, empty_var_bag):
        """Test from_simple_data skips items with empty name."""
        data = [
            {"name": "", "type": FIELD_TYPE_STRING, "value": "value"},
            {"name": "field1", "type": FIELD_TYPE_STRING, "value": "value1"},
        ]
        empty_var_bag.from_simple_data(data)
        assert "" not in empty_var_bag
        assert "field1" in empty_var_bag

    def test_from_simple_data_updates_existing(self, sample_var_bag):
        """Test from_simple_data updates existing fields."""
        data = [
            {
                "name": "test_field",
                "type": FIELD_TYPE_STRING,
                "value": "new_value",
            }
        ]
        sample_var_bag.from_simple_data(data)
        assert sample_var_bag["test_field"] == "new_value"

    def test_from_simple_data_roundtrip(self):
        """Test roundtrip conversion."""
        bag = VarBag()
        field1 = StrField(name="field1")
        field2 = StrField(name="field2")
        bag.add_field(field1, "value1")
        bag.add_field(field2, "value2")
        data = bag.to_simple_data()
        new_bag = VarBag()
        new_bag.from_simple_data(data)
        assert new_bag["field1"] == "value1"
        assert new_bag["field2"] == "value2"
