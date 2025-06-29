from datetime import datetime
from typing import Any, Optional

from attrs import define, field

from exdrf.constants import FIELD_TYPE_DT
from exdrf.field import ExField, FieldInfo


@define
class DateTimeField(ExField):
    """A field that stores moments in time.

    Attributes:
        min: The minimum date-time that can be stored in the field.
        max: The maximum date-time that can be stored in the field.
        format: The format of the date-time string.
    """

    type_name: str = field(default=FIELD_TYPE_DT)

    min: datetime = field(default=None)
    max: datetime = field(default=None)
    format: str = field(default="DD-MM-YYYY HH:mm:ss")

    def __repr__(self) -> str:
        return f"DaTiF(" f"{self.resource.name}.{self.name})"

    def field_properties(self, explicit: bool = False) -> dict[str, Any]:
        result = super().field_properties(explicit)
        if self.min or explicit:
            result["min"] = self.min
        if self.max or explicit:
            result["max"] = self.max
        if self.format or explicit:
            result["format"] = self.format
        return result


class DateTimeInfo(FieldInfo):
    """Parser for information about a date-time field.

    Attributes:
        min: The minimum date-time that can be stored in the field.
        max: The maximum date-time that can be stored in the field.
    """

    min: Optional[datetime] = None
    max: Optional[datetime] = None
