from typing import TYPE_CHECKING, Any

from attrs import define

if TYPE_CHECKING:
    from sqlalchemy import Select

    from exdrf_qt.models.fi_op import FiOp
    from exdrf_qt.models.field import QtField


@define
class SqBaseFiItem:
    """An item in the list of filters.

    The model simply calls the apply method of the filter with the initial
    selection or the selection after the previous filter.
    """

    def apply(self, selection: "Select") -> "Select":
        raise NotImplementedError


@define
class SqFiItem(SqBaseFiItem):

    field: "QtField"
    op: "FiOp"
    value: Any

    def apply(self, selection: "Select") -> "Select":
        return self.op.apply_filter(
            selector=self.field,
            value=self.value,
            selection=selection,
            item=self,
        )
