from typing import List, Tuple

from attrs import define, field

from exdrf.constants import FIELD_TYPE_ENUM
from exdrf.field import ExField, FieldInfo


@define
class EnumField(ExField):
    """A field that stores moments in time.

    Attributes:
        values: The list of possible values for the field.
    """

    type_name: str = field(default=FIELD_TYPE_ENUM)

    enum_values: List[Tuple[str, str]] = field(factory=list)

    def __repr__(self) -> str:
        return f"EnumF(" f"{self.resource.name}.{self.name})"


class EnumInfo(FieldInfo):
    """Parser for information about an enum field.

    Attributes:
        values: The list of possible values for the field.
    """

    enum_values: List[str] = field(factory=list)
