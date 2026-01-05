import logging
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
from exdrf_al.utils import DelChoice
from sqlalchemy import ColumnElement, and_, not_, or_

if TYPE_CHECKING:
    from sqlalchemy import Select  # noqa: F401

    from exdrf_qt.models.field import QtField  # noqa: F401
    from exdrf_qt.models.model import QtModel  # noqa: F401


DBM = TypeVar("DBM")
logger = logging.getLogger(__name__)


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

    def _single_def(self, definition: Any) -> Optional[ColumnElement]:
        """Process a single filter definition.

        A filter definition can be a FieldFilter (or a dict convertible to it),
        or a list representing a logical operation like ["AND", [operands...]].

        Args:
            definition: The filter definition.

        Returns:
            The SQLAlchemy ColumnElement representing the filter, or None.
        """
        if isinstance(definition, dict) or isinstance(definition, FieldFilter):
            # apply_field_filter handles dict conversion to FieldFilter
            return self.apply_field_filter(definition)
        elif isinstance(definition, list):
            if not definition:
                return None  # Or raise an error for empty list definition

            op_keyword = definition[0]
            if not isinstance(op_keyword, str):
                raise ValueError(
                    "Operator in list-based filter definition must be a "
                    f"string. Got: {type(op_keyword)}"
                )
            op_keyword = op_keyword.lower()

            if len(definition) != 2:
                expected_operand_desc = (
                    "the list of operands"
                    if op_keyword in ("and", "or")
                    else "the operand"
                )
                raise ValueError(
                    f"Def for logical op `{op_keyword}` must be 2 items: "
                    f"keyword `{op_keyword}` and {expected_operand_desc}. "
                    f"Got {len(definition)} items."
                )

            operands_or_operand = definition[1]

            if op_keyword == "and":
                if not isinstance(operands_or_operand, list):
                    raise ValueError(
                        "Operands for 'and' operator must be a list. "
                        f"Got: {type(operands_or_operand)}"
                    )
                processed_ops = [
                    res
                    for o in operands_or_operand
                    if (res := self._single_def(o)) is not None
                ]
                return and_(*processed_ops) if processed_ops else None
            elif op_keyword == "or":
                if not isinstance(operands_or_operand, list):
                    raise ValueError(
                        "Operands for 'or' operator must be a list. "
                        f"Got: {type(operands_or_operand)}"
                    )
                processed_ops = [
                    res
                    for o in operands_or_operand
                    if (res := self._single_def(o)) is not None
                ]
                return or_(*processed_ops) if processed_ops else None
            elif op_keyword == "not":
                # operands_or_operand is a single definition here
                processed_operand = self._single_def(operands_or_operand)
                return (
                    not_(processed_operand)
                    if processed_operand is not None
                    else None
                )
            else:
                raise ValueError(
                    f"Unknown logical operator `{op_keyword}` in filter "
                    "definition."
                )
        else:
            raise TypeError(
                f"Invalid filter definition type: {type(definition)}. "
                "Expected dict, FieldFilter, or list."
            )

    def apply_field_filter(
        self, item: Union["FieldFilter", dict]
    ) -> ColumnElement:
        """Apply a field filter to the selection.

        Args:
            item: The field filter to apply (can be a FieldFilter instance or
                a dictionary with 'fld', 'op', and 'vl' keys).

        Returns:
            The SQLAlchemy ColumnElement representing the filter condition.
        """
        f_item: FieldFilter
        if isinstance(item, dict):
            # This is a dictionary with the field name and the filter.
            f_item = FieldFilter(**item)
        else:
            assert isinstance(
                item, FieldFilter
            ), "The field filter must be an instance of FieldFilter."
            f_item = item

        parts = f_item.fld.split(".")
        if len(parts) == 1:
            # Locate this field in our list.
            field = self.fields[f_item.fld]

            # Let the field apply the filter.
            return field.apply_filter(item=f_item, selector=self)
        else:
            field = self.fields[parts[0]]
            return field.apply_sub_filter(
                item=f_item, selector=self, path=parts[1:]
            )

    def apply_subset(self, subset: FilterType) -> List[ColumnElement]:
        """Apply a list of filters.

        The list can consists of individual field filters and the logical
        "and", "or" and "not" operators. "and" and "or" are lists of two
        items: the string keyword ("and" or "or") and the list of filters.
        "not" is also a list of two items: the string keyword ("not") and
        the filter to negate.

        Args:
            subset: The filter subset to apply. Can be empty, a list of field
                filters (dict or FieldFilter instances), or a list representing
                a logical operation like ["AND", [operands...]].

        Returns:
            A list of SQLAlchemy ColumnElement objects representing the applied
            filters. Returns empty list if subset is empty or all filters fail
            to process.
        """
        if not subset:
            return []

        components: List[ColumnElement] = []
        first_item = subset[0]

        # Check if the subset itself is a single logical operation definition
        # e.g., ["AND", [operands...]] or ["NOT", operand]
        if isinstance(first_item, str) and len(subset) == 2:
            op_keyword = first_item.lower()
            operands_or_operand = subset[1]

            if op_keyword == "and":
                if not isinstance(operands_or_operand, list):
                    raise ValueError("Operands for 'and' must be a list.")
                # operands_or_operand is a FilterType (list of definitions)
                # to be processed by a recursive call to apply_subset
                sub_components = self.apply_subset(
                    cast(FilterType, operands_or_operand)
                )
                return [and_(*sub_components)] if sub_components else []
            elif op_keyword == "or":
                if not isinstance(operands_or_operand, list):
                    raise ValueError("Operands for 'or' must be a list.")
                sub_components = self.apply_subset(
                    cast(FilterType, operands_or_operand)
                )
                return [or_(*sub_components)] if sub_components else []
            elif op_keyword == "not":
                # operands_or_operand is a single filter definition
                # (e.g., FieldFilter dict, or another list like ["AND", [...]])
                # This single definition needs to be processed.
                processed_operand = self._single_def(operands_or_operand)
                return (
                    [not_(processed_operand)]
                    if processed_operand is not None
                    else []
                )
            # If op_keyword is not "and", "or", "not", it's not a recognized
            # top-level logical operator. Fall through to treat `subset` as a
            # list of individual filter definitions.

        # If not a recognized top-level logical operator structure, or if it
        # didn't match "and"/"or"/"not", then 'subset' is treated as a list
        # of filter definitions. Each item is a complete definition.
        for definition_item in subset:
            # definition_item can be a FieldFilter (dict/instance) or a list
            # like ["AND", [...]]
            try:
                processed_item = self._single_def(definition_item)
                if processed_item is not None:
                    components.append(processed_item)
            except Exception as e:
                logger.error(
                    "Error applying filter subset %s: %s",
                    definition_item,
                    e,
                    exc_info=True,
                )

        return components

    def run(self, filters: "FilterType") -> "Select":
        """Run the selection.

        The function applies the filters to the base selection and returns
        the SQLAlchemy select statement with the filters applied. Joins are
        applied before filters.

        Args:
            filters: The filters to apply. Can be empty, a list of field filters
                (dict or FieldFilter instances), or complex logical operations.

        Returns:
            The SQLAlchemy select statement with joins and filters applied.
            Returns the base selection if no filters are provided.
        """
        base = self.base

        # See if the model has a deleted field and apply that.
        if self.qt_model is not None:
            del_field = self.qt_model.get_soft_delete_field()
            if del_field is not None:
                del_choice = self.qt_model.del_choice
                if del_choice == DelChoice.DELETED:
                    base = base.where(del_field.is_(True))
                elif del_choice == DelChoice.ACTIVE:
                    base = base.where(
                        del_field.is_(None) | del_field.is_(False)
                    )
                elif del_choice == DelChoice.ALL:
                    logger.log(
                        1,
                        "M: %s DelChoice.ALL, so no del filter applied",
                        self.qt_model.name,
                    )
                else:
                    assert False, f"Invalid DelChoice {del_choice}"
            else:
                logger.log(
                    1,
                    "No soft delete field found for model %s",
                    self.qt_model.name,
                )

        components = self.apply_subset(filters)
        if not components:
            # No filters to apply.
            return base

        # Apply the joins to the base selection.
        for join in self.joins:
            if isinstance(join, (tuple, list)):
                if isinstance(join[-1], dict):
                    join_kwargs = join[-1]
                    join = join[:-1]
                else:
                    join_kwargs = {}

                base = base.join(*join, **join_kwargs)
            else:
                base = base.join(join)

        # Apply the filters to the base selection.
        return base.where(*components)

    @classmethod
    def from_qt_model(cls, qt_model: "QtModel[DBM]") -> "Selector":
        """Create a selector from a Qt model.

        Args:
            qt_model: The Qt model instance to create the selector from.

        Returns:
            A new Selector instance configured with the model's database model,
            base selection, and fields.
        """
        return cls(
            db_model=qt_model.db_model,
            base=qt_model.base_selection,
            fields={f.name: f for f in qt_model.fields},
            qt_model=qt_model,
        )
