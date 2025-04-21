from typing import Optional

from attrs import define, field

from exdrf.constants import FIELD_TYPE_STRING
from exdrf.field import ExField, FieldInfo


@define
class StrField(ExField):
    """A field that stores strings.

    Attributes:
        multiline: Whether the string can span multiple lines.
        min_length: The minimum length of the string.
        max_length: The maximum length of the string.
    """

    type_name: str = field(default=FIELD_TYPE_STRING)

    multiline: bool = field(default=False)
    min_length: int = field(default=None)
    max_length: int = field(default=None)

    def __repr__(self) -> str:
        return f"StrF(" f"{self.resource.name}.{self.name})"


class StrInfo(FieldInfo):
    """Parser for information about a string field."""

    multiline: Optional[bool] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
