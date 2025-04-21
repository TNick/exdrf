from attrs import define, field

from exdrf.constants import FIELD_TYPE_STRING_LIST
from exdrf.field import ExField, FieldInfo


@define
class StrListField(ExField):
    """A field that stores list of strings."""

    type_name: str = field(default=FIELD_TYPE_STRING_LIST)

    def __repr__(self) -> str:
        return f"SListF(" f"{self.resource.name}.{self.name})"


class StrListInfo(FieldInfo):
    """Parser for information about a string-list field."""
