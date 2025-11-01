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
        """Apply this filter item to the selection.

        Args:
            selection: The SQLAlchemy select statement to apply the filter to.

        Returns:
            A new select statement with the filter applied.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        raise NotImplementedError


@define
class SqFiItem(SqBaseFiItem):
    """A concrete filter item that applies an operator to a field.

    Attributes:
        field: The field (column) to filter on.
        op: The filter operator to apply.
        value: The value to compare against.
    """

    field: "QtField"
    op: "FiOp"
    value: Any

    def apply(self, selection: "Select") -> "Select":
        """Apply this filter item to the selection.

        Uses the operator's apply_filter method to apply the filter to the
        given selection.

        Args:
            selection: The SQLAlchemy select statement to apply the filter to.

        Returns:
            A new select statement with the filter applied.
        """
        return self.op.apply_filter(
            selector=self.field,
            value=self.value,
            selection=selection,
            item=self,
        )
