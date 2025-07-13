from typing import Any, List, Optional, Tuple

from attrs import define, field
from pydantic import Field, field_validator

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
    enum_values: List[Tuple[int, str]] = field(factory=list)

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
        if self.enum_values or explicit:
            result["enum_values"] = self.enum_values
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
    enum_values: List[Tuple[int, str]] = Field(default_factory=list)

    @field_validator("enum_values", mode="before")
    @classmethod
    def validate_enum_values(cls, v):
        """Validate the enum values.

        Accepts either a list of (int, str) tuples or an Enum class.
        """
        return cls.validate_enum_with_type(v, int)
