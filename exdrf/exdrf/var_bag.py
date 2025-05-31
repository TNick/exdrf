import re
from typing import Any, Dict, Iterator, List, Tuple

from attrs import define, field

from exdrf.field import ExField


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

    @property
    def as_dict(self) -> Dict[str, Any]:
        """Return a dictionary of the variables in the bag and their values."""
        return {fld.name: self[fld.name] for fld in self.fields}
