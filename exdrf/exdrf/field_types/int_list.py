from attrs import define, field

from exdrf.constants import FIELD_TYPE_INT_LIST
from exdrf.field import ExField, FieldInfo


@define
class IntListField(ExField):
    """A field that stores list of integers."""

    type_name: str = field(default=FIELD_TYPE_INT_LIST)

    def __repr__(self) -> str:
        return f"IntListF(" f"{self.resource.name}.{self.name})"


class IntListInfo(FieldInfo):
    """Parser for information about an integer-list field."""
