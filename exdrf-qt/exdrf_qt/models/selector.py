from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

from attrs import define, field
from exdrf.filter import FieldFilter, FilterType
from sqlalchemy import ColumnElement, and_, not_, or_

if TYPE_CHECKING:
    from sqlalchemy import Select  # noqa: F401

    from exdrf_qt.models.field import QtField  # noqa: F401
    from exdrf_qt.models.model import QtModel  # noqa: F401


DBM = TypeVar("DBM")


@define
class Selector(Generic[DBM]):
    """A select constructor.

    This class is used to build a SQLAlchemy select statement for the model.

    Attributes:
        db_model: The database model class.
        base: The base SQLAlchemy select statement for the model.
        joins: A list of SQLAlchemy select statements that are joined to the
            base statement.
        depth: The depth of logic (each and, or, not operator increases
            the depth).
        qt_model: The Qt model that requested this selection.
    """

    db_model: Type[DBM]
    base: "Select"
    joins: List[Any] = field(factory=list)
    depth: int = field(default=0)
    fields: Dict[str, "QtField[DBM]"] = field(factory=dict)
    qt_model: Optional["QtModel"] = field(default=None)

    def apply_field_filter(
        self, item: Union["FieldFilter", dict]
    ) -> ColumnElement:
        """Apply a field filter to the selection.

        Args:
            item: The field filter to apply.

        Returns:
            The SQLAlchemy select statement with the filter applied.
        """
        if isinstance(item, dict):
            # This is a dictionary with the field name and the filter.
            item = FieldFilter(**item)
        else:
            assert isinstance(
                item, FieldFilter
            ), "The field filter must be an instance of FieldFilter."

        # Locate this field in our list.
        field = self.fields[item.fld]

        # Let the field apply the filter.
        return field.apply_filter(item=item, selector=self)  # type: ignore

    def apply_subset(self, subset: FilterType):
        """Apply a list of filters.

        The list can consists of individual field filters and the logical
        "and", "or" and "not" operators. "and" and "or" are lists of two
        items: the string keyword ("and" or "or") and the list of filters.
        "not" is also a list of two items: the string keyword ("not") and
        the filter to negate.
        """
        components = []

        for i, v in enumerate(subset):
            if i == 0:
                if isinstance(v, str):
                    # This is a keyword for the logical operator.
                    assert len(subset) == 2, (
                        f"The definition for the logical operator `{v}` "
                        "must be a list of two items: "
                        "the keyword `{v}` and the "
                        + (
                            "list of filters."
                            if v in ("and", "or")
                            else "the filter to negate."
                        )
                    )
                    if v == "and":
                        return [and_(*self.apply_subset(cast(Any, subset[1])))]
                    elif v == "or":
                        return [or_(*self.apply_subset(cast(Any, subset[1])))]
                    elif v == "not":
                        return [
                            not_(
                                self.apply_field_filter(
                                    cast(FieldFilter, subset[1])
                                )
                            )
                        ]
                    else:
                        raise ValueError(f"Unknown logical operator `{v}`.")
            # This is a filter for a field.
            f_result = self.apply_field_filter(cast(FieldFilter, v))
            if f_result is not None:
                components.append(f_result)

        return components

    def run(self, filters: "FilterType") -> "Select":
        """Run the selection.

        The function applies the filters to the base selection and returns
        the SQLAlchemy select statement with the filters applied.

        Returns:
            The SQLAlchemy select statement with the filters applied.
        """
        components = self.apply_subset(filters)
        if not components:
            # No filters to apply.
            return self.base

        # Apply the joins to the base selection.
        base = self.base
        for join in self.joins:
            base = base.join(join)

        # Apply the filters to the base selection.
        return base.where(*components)

    @classmethod
    def from_qt_model(cls, qt_model: "QtModel[DBM]") -> "Selector":
        """Create a constructor from a Qt model."""
        return cls(
            db_model=qt_model.db_model,
            base=qt_model.base_selection,
            fields={f.name: f for f in qt_model.fields},
            qt_model=qt_model,
        )
