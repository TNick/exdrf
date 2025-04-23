from typing import TYPE_CHECKING, List

from attrs import define, field

from exdrf.constants import FIELD_TYPE_SORT
from exdrf.field import ExField

if TYPE_CHECKING:
    from exdrf.dataset import ExDataset
    from exdrf.resource import ExResource


@define
class SortField(ExField):
    type_name: str = field(default=FIELD_TYPE_SORT)

    def extra_ref(self, d_set: "ExDataset") -> List["ExResource"]:
        return [d_set["SortItem"]]
