from datetime import time
from typing import Optional

from attrs import define, field

from exdrf.constants import FIELD_TYPE_TIME
from exdrf.field import ExField, FieldInfo


@define
class TimeField(ExField):
    """A field that stores a time of day (without a date)

    Attributes:
        min: The minimum time that can be stored in the field.
        max: The maximum time that can be stored in the field.
        format: The format of the time string.
    """

    type_name: str = field(default=FIELD_TYPE_TIME)

    min: time = field(default=None)
    max: time = field(default=None)
    format: str = field(default="HH:mm:ss")

    def __repr__(self) -> str:
        return f"TimeF(" f"{self.resource.name}.{self.name})"


class TimeInfo(FieldInfo):
    """Parser for information about a date-time field.

    Attributes:
        min: The minimum time that can be stored in the field.
        max: The maximum time that can be stored in the field.
    """

    min: Optional[time] = None
    max: Optional[time] = None
