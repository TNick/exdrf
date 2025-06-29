from typing import Any, Optional

from attrs import define, field

from exdrf.constants import FIELD_TYPE_INTEGER
from exdrf.field import ExField, FieldInfo


@define
class IntField(ExField):
    """A field that stores integers.

    Attributes:
        min: The minimum integer that can be stored in the field (inclusive).
        max: The maximum integer that can be stored in the field (inclusive).
        unit: The unit of measurement for the field.
        unit_symbol: The symbol for the unit of measurement.
    """

    type_name: str = field(default=FIELD_TYPE_INTEGER)

    min: int = field(default=None)
    max: int = field(default=None)
    unit: str = field(default=None)
    unit_symbol: str = field(default=None)

    def __repr__(self) -> str:
        return f"IntF(" f"{self.resource.name}.{self.name})"

    def field_properties(self, explicit: bool = False) -> dict[str, Any]:
        result = super().field_properties(explicit)
        if self.min is not None or explicit:
            result["min"] = self.min
        if self.max is not None or explicit:
            result["max"] = self.max
        if self.unit or explicit:
            result["unit"] = self.unit
        if self.unit_symbol or explicit:
            result["unit_symbol"] = self.unit_symbol
        return result


class IntInfo(FieldInfo):
    """Parser for information about an integer field.

    Attributes:
        min: The minimum integer that can be stored in the field.
        max: The maximum integer that can be stored in the field.
        unit: The unit of measurement for the field.
        unit_symbol: The symbol for the unit of measurement.
    """

    min: Optional[int] = None
    max: Optional[int] = None
    unit: Optional[str] = None
    unit_symbol: Optional[str] = None
