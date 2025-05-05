from datetime import date
from typing import Optional

from attrs import define, field

from exdrf.constants import FIELD_TYPE_DATE
from exdrf.field import ExField, FieldInfo


@define
class DateField(ExField):
    """A field that stores moments in time.

    Attributes:
        min: The minimum date that can be stored in the field.
        max: The maximum date that can be stored in the field.
        format: The format of the date string.
    """

    type_name: str = field(default=FIELD_TYPE_DATE)

    min: date = field(default=None)
    max: date = field(default=None)
    format: str = field(default="DD-MM-YYYY")

    def __repr__(self) -> str:
        return f"DaTiF(" f"{self.resource.name}.{self.name})"


class DateInfo(FieldInfo):
    """Parser for information about a date-time field.

    Attributes:
        min: The minimum date that can be stored in the field.
        max: The maximum date that can be stored in the field.
    """

    min: Optional[date] = None
    max: Optional[date] = None
