from attrs import define, field

from exdrf.constants import FIELD_TYPE_FLOAT_LIST
from exdrf.field import ExField, FieldInfo


@define
class FloatListField(ExField):
    """A field that stores list of real numbers."""

    type_name: str = field(default=FIELD_TYPE_FLOAT_LIST)

    def __repr__(self) -> str:
        return f"FloatListF(" f"{self.resource.name}.{self.name})"


class FloatListInfo(FieldInfo):
    """Parser for information about a real-numbers list field."""
