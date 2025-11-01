import re
from datetime import date, datetime
from typing import Any, Dict, Iterator, List, Tuple

from attrs import define, field

from exdrf.field import ExField
from exdrf.field_types.api import (
    FIELD_TYPE_STRING,
    DateTimeField,
    StrField,
    field_type_to_class,
)


@define
class VarBag:
    """A bag of variables for a template.

    Attributes:
        values: Dictionary of values to be used in the template. This is the
            source of truth for what variables exist.
        _fields: Dictionary mapping field names to ExField objects.
    """

    values: Dict[str, Any] = field(factory=dict)
    _fields: Dict[str, "ExField"] = field(factory=dict, init=False, repr=False)

    @property
    def fields(self) -> List["ExField"]:
        """List of fields, ordered by keys in values."""
        return list(self._fields.values())

    @property
    def var_names(self) -> List[str]:
        """List of variable names."""
        return list(self.values.keys())

    @property
    def var_values(self) -> List[str]:
        """List of variable values."""
        return [self.values[name] for name in self.values.keys()]

    @property
    def field_names(self) -> List[str]:
        """List of field names."""
        return list(self.values.keys())

    @property
    def field_values(self) -> List[Any]:
        """List of field values."""
        return [self.values[name] for name in self.values.keys()]

    @property
    def field_count(self) -> int:
        """Count of fields."""
        return len(self.values)

    @property
    def as_field_dict(self) -> Dict[str, Any]:
        """Return a dictionary mapping field names to values."""
        return dict((name, self.values[name]) for name in self._fields.keys())

    def add_field(self, field: "ExField", value: Any = None):
        """Add a field to the bag.

        Args:
            field: The field to add.
            value: The value to add to the field.
        """
        self._fields[field.name] = field
        self.values[field.name] = value

    def add_fields(self, fields: List[Tuple["ExField", Any]]):
        """Add a list of fields to the bag.

        Args:
            fields: List of fields to add.
        """
        for fld, value in fields:
            self._fields[fld.name] = fld
            self.values[fld.name] = value

    def contains_field(self, name: str) -> bool:
        """Check if a field exists.

        Args:
            name: The name of the field to check.

        Returns:
            True if the field exists, False otherwise.
        """
        return name in self.values

    def is_field(self, name: str) -> bool:
        """Check if a value has an associated ExField object.

        Args:
            name: The name of the value to check.

        Returns:
            True if the value has an associated ExField object, False if it
            is a raw value without a field definition.
        """
        return name in self._fields

    def get_field_value(self, name: str) -> Any:
        """Get the value of a field.

        Args:
            name: The name of the field.

        Returns:
            The value of the field.

        Raises:
            KeyError: If the field does not exist.
        """
        if name not in self.values:
            raise KeyError(f"Key {name} not found")
        if name not in self._fields:
            raise KeyError(f"Key {name} is not a field")
        return self.values[name]

    def set_field_value(self, name: str, value: Any) -> None:
        """Set the value of a field.

        Args:
            name: The name of the field.
            value: The value to set.

        Raises:
            KeyError: If the field does not exist.
        """
        if name not in self._fields:
            raise KeyError(f"Key {name} is not a field")
        self.values[name] = value

    def __contains__(self, key: str) -> bool:
        return key in self.values

    def __getitem__(self, key: str) -> Any:
        if key not in self.values:
            raise KeyError(f"Key {key} not found")
        return self.values[key]

    def __setitem__(self, key: str, value: Any) -> None:
        if key not in self.values:
            raise KeyError(f"Key {key} not found")
        self.values[key] = value

    def __iter__(self) -> Iterator[str]:
        """Return an iterator of keys for dictionary unpacking."""
        yield from self.values.keys()

    def __len__(self) -> int:
        """Return the number of fields that have values."""
        return len(self.values)

    def filtered(self, by_name: bool, text: str, exact: bool):
        """Filter the variable bag based on name or value.

        Args:
            by_name: If True, filter by field name; if False, filter by value.
            text: The text pattern to search for (supports % and * wildcards).
            exact: If True, match exactly; if False, match anywhere.

        Returns:
            A new VarBag containing only the filtered fields.
        """
        if len(text) == 0:
            return self

        # Convert wildcard pattern to regex pattern
        pattern = text.replace("%", ".*").replace("*", ".*")
        if exact:
            pattern = f"^{pattern}$"
        regex = re.compile(pattern, re.IGNORECASE)

        result = VarBag()
        for name in self.values.keys():
            search_text = (
                name.lower() if by_name else str(self.values[name]).lower()
            )
            if regex.search(search_text):
                if name in self._fields:
                    result._fields[name] = self._fields[name]
                result.values[name] = self.values[name]
        return result

    def filtered_fields(self, by_name: bool, text: str, exact: bool):
        """Filter fields based on name or value.

        Args:
            by_name: If True, filter by field name; if False, filter by value.
            text: The text pattern to search for (supports % and * wildcards).
            exact: If True, match exactly; if False, match anywhere.

        Returns:
            A new VarBag containing only the filtered fields.
        """
        if len(text) == 0:
            return self

        # Convert wildcard pattern to regex pattern
        pattern = text.replace("%", ".*").replace("*", ".*")
        if exact:
            pattern = f"^{pattern}$"
        regex = re.compile(pattern, re.IGNORECASE)

        result = VarBag()
        for name in self._fields.keys():
            search_text = (
                name.lower() if by_name else str(self.values[name]).lower()
            )
            if regex.search(search_text):
                result._fields[name] = self._fields[name]
                result.values[name] = self.values[name]
        return result

    def add_now(self):
        """Add the current date and time to the variable bag."""
        self.add_field(DateTimeField(name="now"), datetime.now())

    @property
    def as_dict(self) -> Dict[str, Any]:
        """Return a dictionary of the variables in the bag and their values."""
        return dict(self.values)

    def simplify_value(self, value: Any) -> Any:
        """Convert a value to a simple value.

        The simple values are:
        - int
        - float
        - bool
        - str
        - list of simple values
        - dict of simple values

        Classes that are not one of those will be converted to a string
        with the class name.
        """
        if isinstance(value, (list, tuple)):
            return [self.simplify_value(v) for v in value]
        elif isinstance(value, dict):
            return {k: self.simplify_value(v) for k, v in value.items()}
        elif isinstance(value, (str, int, float, bool)):
            return value
        elif isinstance(value, datetime):
            return value.strftime("%Y-%m-%dT%H:%M:%S")
        elif isinstance(value, date):
            return value.strftime("%Y-%m-%d")
        else:
            return f"<{value.__class__.__name__}>"

    def to_simple_data(self) -> List[Dict[str, Any]]:
        """Convert the variable bag to a simple data structure.

        The result is a list of dictionaries, each containing the name,
        type, and value of a variable.

        The simple values are:
        - int
        - float
        - bool
        - str
        - list
        - dict

        Classes that are not one of those will be converted to a string
        with the class name.
        """
        result = []
        for name in self.values.keys():
            fld = self._fields.get(name)
            type_name = fld.type_name if fld else FIELD_TYPE_STRING
            result.append(
                {
                    "name": name,
                    "type": type_name,
                    "value": self.simplify_value(self.values[name]),
                }
            )
        return result

    def from_simple_data(self, data: Any):
        """Populate the variable bag from a simple data structure.

        The simple data structure is a list of dictionaries, each
        containing the name, type, and value of a variable.
        """
        for item in data:
            type_name = item.get("type", FIELD_TYPE_STRING)
            cls_for_type = field_type_to_class.get(type_name, StrField)
            name = item.get("name", "")
            if not name:
                continue
            if name not in self.values:
                inst = cls_for_type(name=name)
                self._fields[name] = inst
            else:
                inst = self._fields.get(name)
                if inst is None:
                    inst = cls_for_type(name=name)
                    self._fields[name] = inst
            self.values[name] = inst.value_from_str(item.get("value", ""))
