from attrs import define, field

from exdrf.constants import FIELD_TYPE_STRING_LIST
from exdrf.field_types.str_field import StrField, StrInfo


@define
class StrListField(StrField):
    """A field that stores list of strings."""

    type_name: str = field(default=FIELD_TYPE_STRING_LIST)

    def __repr__(self) -> str:
        return f"SListF(" f"{self.resource.name}.{self.name})"


class StrListInfo(StrInfo):
    """Parser for information about a string-list field."""
