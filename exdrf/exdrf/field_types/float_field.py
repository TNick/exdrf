from typing import Optional

from attrs import define, field

from exdrf.constants import FIELD_TYPE_FLOAT
from exdrf.field import ExField, FieldInfo


@define
class FloatField(ExField):
    """A field that stores real numbers.

    Attributes:
        min: The minimum value that can be stored in the field.
        max: The maximum value that can be stored in the field.
        precision: The number of digits that can be stored in the field.
        scale: The number of digits to the right of the decimal point.
        unit: The unit of measurement for the field.
        unit_symbol: The symbol for the unit of measurement.
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
    """Parser for information about a real-number field.

    Attributes:
        min: The minimum value that can be stored in the field.
        max: The maximum value that can be stored in the field.
        precision: The number of digits that can be stored in the field.
        scale: The number of digits to the right of the decimal point.
        unit: The unit of measurement for the field.
        unit_symbol: The symbol for the unit of measurement.
    """

    min: Optional[float] = None
    max: Optional[float] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    unit: Optional[str] = None
    unit_symbol: Optional[str] = None
