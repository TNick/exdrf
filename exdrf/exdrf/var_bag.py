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
        fields: List of fields to be used in the template.
        values: Dictionary of values to be used in the template.
    """

    fields: List["ExField"] = field(factory=list)
    values: Dict[str, Any] = field(factory=dict)

    @property
    def var_names(self) -> List[str]:
        return [f.name for f in self.fields]

    @property
    def var_values(self) -> List[str]:
        return [self[f.name] for f in self.fields]

    def add_field(self, field: "ExField", value: Any = None):
        """Add a field to the bag.

        Args:
            field: The field to add.
            value: The value to add to the field.
        """
        for i, fld in enumerate(self.fields):
            if fld.name == field.name:
                self.fields[i] = field
                break
        else:
            self.fields.append(field)
        self.values[field.name] = value

    def add_fields(self, fields: List[Tuple["ExField", Any]]):
        """Add a list of fields to the bag.

        Args:
            fields: List of fields to add.
        """
        crt_set = dict((f.name, i) for i, f in enumerate(self.fields))
        for fld, value in fields:
            crt_pos = crt_set.get(fld.name)
            if crt_pos is not None:
                self.fields[crt_pos] = fld
            else:
                self.fields.append(fld)
            self.values[fld.name] = value

    def __contains__(self, key: str) -> bool:
        for fld in self.fields:
            if fld.name == key:
                return True
        return False

    def __getitem__(self, key: str) -> Any:
        for fld in self.fields:
            if fld.name == key:
                return self.values.get(fld.name)
        raise KeyError(f"Key {key} not found in {self.fields}")

    def __setitem__(self, key: str, value: Any) -> None:
        for fld in self.fields:
            if fld.name == key:
                self.values[fld.name] = value
                return
        raise KeyError(f"Key {key} not found in {self.fields}")

    def __iter__(self) -> Iterator[str]:
        """Return an iterator of keys for dictionary unpacking."""
        for fld in self.fields:
            if fld.name in self.values:
                yield fld.name

    def __len__(self) -> int:
        """Return the number of fields that have values."""
        return len(self.values)

    def filtered(self, by_name: bool, text: str, exact: bool):
        if len(text) == 0:
            return self

        # Convert wildcard pattern to regex pattern
        pattern = text.replace("%", ".*").replace("*", ".*")
        if exact:
            pattern = f"^{pattern}$"
        regex = re.compile(pattern, re.IGNORECASE)

        result = VarBag()
        for fld in self.fields:
            search_text = (
                fld.name.lower() if by_name else str(self[fld.name]).lower()
            )
            if regex.search(search_text):
                result.fields.append(fld)
                result.values[fld.name] = self[fld.name]
        return result

    def add_now(self):
        """Add the current date and time to the variable bag."""
        self.add_field(DateTimeField(name="now"), datetime.now())

    @property
    def as_dict(self) -> Dict[str, Any]:
        """Return a dictionary of the variables in the bag and their values."""
        return {fld.name: self[fld.name] for fld in self.fields}

    def simplify_value(self, value: Any) -> Any:
        """Convert a value to a simple value.

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
        for fld in self.fields:
            result.append(
                {
                    "name": fld.name,
                    "type": fld.type_name,
                    "value": self.simplify_value(self[fld.name]),
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
            if name not in self:
                inst = cls_for_type(name=name)
                self.add_field(inst)
            else:
                inst = self.fields[self.var_names.index(name)]
            self[name] = inst.value_from_str(item.get("value", ""))
