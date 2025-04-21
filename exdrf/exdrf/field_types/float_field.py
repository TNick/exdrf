from typing import Optional

from attrs import define, field

from exdrf.constants import FIELD_TYPE_FLOAT
from exdrf.field import ExField, FieldInfo


@define
class FloatField(ExField):
    """A field that stores real numbers.

    Attributes:
        true_str: The string representation of the boolean value `True`.
        false_str: The string representation of the boolean value `False`.
    """

    type_name: str = field(default=FIELD_TYPE_FLOAT)

    min: float = field(default=None)
    max: float = field(default=None)
    precision: int = field(default=None)
    scale: int = field(default=None)
    unit: str = field(default=None)
    unit_symbol: str = field(default=None)

    def __repr__(self) -> str:
        return f"FloatF(" f"{self.resource.name}.{self.name})"


class FloatInfo(FieldInfo):
    """Parser for information about a real-number field."""

    min: Optional[float] = None
    max: Optional[float] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    unit: Optional[float] = None
    unit_symbol: Optional[float] = None
