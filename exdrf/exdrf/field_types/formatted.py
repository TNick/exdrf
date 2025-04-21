from typing import Literal, Optional

from attrs import define, field

from exdrf.constants import FIELD_TYPE_FORMATTED
from exdrf.field import FieldInfo
from exdrf.field_types.str_field import StrField


@define
class FormattedField(StrField):
    """A field that stores strings that contain both text and markup.

    Attributes:
        format: The format of the string. Can be "json", "html", or "xml".
    """

    type_name: str = field(default=FIELD_TYPE_FORMATTED)

    format: Literal["json", "html", "xml"] = field(default="json")

    def __repr__(self) -> str:
        return f"StrF(" f"{self.resource.name}.{self.name})"


class FormattedInfo(FieldInfo):
    """Parser for information about a string field."""

    format: Optional[Literal["json", "html", "xml"]] = None
