from typing import Any, Optional

from attrs import define, field

from exdrf.constants import FIELD_TYPE_BOOL
from exdrf.field import ExField, FieldInfo


@define
class BoolField(ExField):
    """A field that stores boolean values.

    This field is not expected to resize when in list view mode.

    Attributes:
        true_str: The string representation of the boolean value `True`.
        false_str: The string representation of the boolean value `False`.
    """

    type_name: str = field(default=FIELD_TYPE_BOOL)
    resizable: bool = field(default=False)

    true_str: str = field(default="True")
    false_str: str = field(default="False")

    def __repr__(self) -> str:
        return f"BoolF(" f"{self.resource.name}.{self.name})"

    def field_properties(self, explicit: bool = False) -> dict[str, Any]:
        result = super().field_properties(explicit)
        if self.true_str or explicit:
            result["true_str"] = self.true_str
        if self.false_str or explicit:
            result["false_str"] = self.false_str
        return result


class BoolInfo(FieldInfo):
    """Parser for information about a boolean field.

    Attributes:
        true_str: The string representation of the boolean value `True`.
        false_str: The string representation of the boolean value `False`.
    """

    true_str: Optional[str] = None
    false_str: Optional[str] = None
