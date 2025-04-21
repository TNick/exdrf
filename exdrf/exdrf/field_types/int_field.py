from typing import Optional

from attrs import define, field

from exdrf.constants import FIELD_TYPE_INTEGER
from exdrf.field import ExField, FieldInfo


@define
class IntField(ExField):
    """A field that stores integers.

    Attributes:
        true_str: The string representation of the boolean value `True`.
        false_str: The string representation of the boolean value `False`.
    """

    type_name: str = field(default=FIELD_TYPE_INTEGER)

    min: int = field(default=None)
    max: int = field(default=None)
    unit: str = field(default=None)
    unit_symbol: str = field(default=None)

    def __repr__(self) -> str:
        return f"IntF(" f"{self.resource.name}.{self.name})"


class IntInfo(FieldInfo):
    """Parser for information about an integer field."""

    min: Optional[int] = None
    max: Optional[int] = None
    unit: Optional[int] = None
    unit_symbol: Optional[int] = None
