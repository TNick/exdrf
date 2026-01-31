import logging
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import or_, select
from sqlalchemy.inspection import inspect

if TYPE_CHECKING:
    from sqlalchemy import Select

logger = logging.getLogger(__name__)


class DelChoice(Enum):
    """Used with selectors to indicate which subset of records to select.

    DELETED: Only deleted records.
    ACTIVE: Only not deleted records.
    ALL: All records.
    """

    DELETED = -1
    ACTIVE = 1
    ALL = 0

    def apply(
        self, OrmClass: type, sel: "Select", del_field: str = "deleted"
    ) -> "Select":
        """Apply the choice to a select statement.

        The record is assumed to be deleted if the `del_field` column/field is
        True. If the `del_field` column/field is None or false, the record is
        assumed to not have been deleted.

        Args:
            OrmClass: The ORM class to apply the choice to.
            sel: The select statement to apply the choice to.

        Returns:
            The select statement with the choice applied.
        """
        fld = getattr(OrmClass, del_field, None)
        assert (
            fld is not None
        ), f"OrmClass must have a `{del_field}` column/field"

        if self == DelChoice.DELETED:
            return sel.where(fld.is_(True))
        elif self == DelChoice.ACTIVE:
            return sel.where(or_(fld.is_(None), fld.is_(False)))
        else:
            return sel

    def create(self, OrmClass: type, del_field: str = "deleted") -> "Select":
        """Create a select statement for the choice.

        The record is assumed to be deleted if the `del_field` column/field is
        True. If the `del_field` column/field is None or false, the record is
        assumed to not have been deleted.

        Args:
            OrmClass: The ORM class to create a select statement for.
                It is assumed that the class has a `del_field` column/field.

        Returns:
            A select statement for the choice.
        """
        fld = getattr(OrmClass, del_field, None)
        assert (
            fld is not None
        ), f"OrmClass must have a `{del_field}` column/field"
        sel = select(OrmClass)
        if self == DelChoice.DELETED:
            return sel.where(fld.is_(True))
        elif self == DelChoice.ACTIVE:
            return sel.where(or_(fld.is_(None), fld.is_(False)))
        else:
            return sel


def identity_value(item: Any) -> Any:
    """Extract the identity for a SQLAlchemy instance without loading it."""
    try:
        state = inspect(item)
    except Exception:
        logger.exception("Failed to inspect value %s", item)
        return None
    if state is None or state.identity is None:
        return None
    if isinstance(state.identity, (list, tuple)) and len(state.identity) == 1:
        return state.identity[0]
    return state.identity
