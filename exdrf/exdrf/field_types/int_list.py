from attrs import define, field

from exdrf.constants import FIELD_TYPE_INT_LIST
from exdrf.field_types.int_field import IntField, IntInfo


@define
class IntListField(IntField):
    """A field that stores a list of integers."""

    type_name: str = field(default=FIELD_TYPE_INT_LIST)

    def __repr__(self) -> str:
        return f"IntListF(" f"{self.resource.name}.{self.name})"


class IntListInfo(IntInfo):
    """Parser for information about an integer-list field."""
