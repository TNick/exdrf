from typing import Any, Optional

from attrs import define, field

from exdrf.constants import FIELD_TYPE_DURATION
from exdrf.field import ExField, FieldInfo


@define
class DurationField(ExField):
    """A field that stores the duration of time.

    Attributes:
        min: The minimum duration that can be stored in the field.
        max: The maximum duration that can be stored in the field.
    """

    type_name: str = field(default=FIELD_TYPE_DURATION)

    min: float = field(default=None)
    max: float = field(default=None)

    def __repr__(self) -> str:
        return f"DaTiF(" f"{self.resource.name}.{self.name})"

    def field_properties(self, explicit: bool = False) -> dict[str, Any]:
        result = super().field_properties(explicit)
        if self.min or explicit:
            result["min"] = self.min
        if self.max or explicit:
            result["max"] = self.max
        return result


class DurationInfo(FieldInfo):
    """Parser for information about a time duration field.

    Attributes:
        min: The minimum duration that can be stored in the field.
        max: The maximum duration that can be stored in the field.
    """

    min: Optional[float] = None
    max: Optional[float] = None
