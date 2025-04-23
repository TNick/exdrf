from attrs import define, field

from exdrf.constants import FIELD_TYPE_FILTER
from exdrf.field import ExField


@define
class FilterField(ExField):
    """Field for filtering results."""

    type_name: str = field(default=FIELD_TYPE_FILTER)
