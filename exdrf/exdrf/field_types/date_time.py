from datetime import datetime
from typing import Optional

from attrs import define, field

from exdrf.constants import FIELD_TYPE_DT
from exdrf.field import ExField, FieldInfo


@define
class DateTimeField(ExField):
    """A field that stores moments in time.

    Attributes:
        min: The minimum date-time that can be stored in the field.
        max: The maximum date-time that can be stored in the field.
    """

    type_name: str = field(default=FIELD_TYPE_DT)

    min: datetime = field(default=None)
    max: datetime = field(default=None)

    def __repr__(self) -> str:
        return f"DaTiF(" f"{self.resource.name}.{self.name})"


class DateTimeInfo(FieldInfo):
    """Parser for information about a date-time field.

    Attributes:
        min: The minimum date-time that can be stored in the field.
        max: The maximum date-time that can be stored in the field.
    """

    min: Optional[datetime] = None
    max: Optional[datetime] = None
