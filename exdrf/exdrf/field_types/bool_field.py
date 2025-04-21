from typing import Optional

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


class BoolInfo(FieldInfo):
    """Parser for information about a boolean field."""

    true_str: Optional[str] = None
    false_str: Optional[str] = None
