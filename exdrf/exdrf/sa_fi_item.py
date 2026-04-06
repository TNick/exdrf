"""SQLAlchemy-oriented filter list items (Qt-free)."""

from typing import TYPE_CHECKING, Any

from attrs import define

from exdrf.sa_filter_op import FiOp

if TYPE_CHECKING:
    from sqlalchemy import Select


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
        field: The field (column descriptor) to filter on; often a Qt model
            field or other object whose paired operator implements
            ``apply_filter``.
        op: The filter operator to apply.
        value: The value to compare against.
    """

    field: Any
    op: FiOp
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
