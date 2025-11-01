import logging
from typing import Any, Union

from attrs import define, field
from sqlalchemy import String
from sqlalchemy import cast as al_cast
from sqlalchemy.sql.operators import (
    _operator_fn,
    comparison_op,
    eq,
    gt,
    ilike_op,
    in_op,
    lt,
    ne,
    regexp_match_op,
)

logger = logging.getLogger(__name__)


@define
class FiOp:
    """Base class for operators.

    Attributes:
        uniq: The name of the operator.
        predicate: The predicate function used by the operator.
    """

    uniq: str
    predicate: Any


@define
class EqFiOp(FiOp):
    """General equality operator.

    Attributes:
        uniq: The name of the operator, set to "eq".
        predicate: The equality predicate function.
    """

    uniq: str = field(default="eq", init=False)
    predicate: Any = field(default=eq)


@define
class NotEqFiOp(FiOp):
    """Not equal operator.

    Attributes:
        uniq: The name of the operator, set to "not_eq".
        predicate: The not equal predicate function.
    """

    uniq: str = field(default="not_eq", init=False)
    predicate: Any = field(default=ne)


@define
class ILikeFiOp(FiOp):
    """Case-insensitive pattern matching operator.

    The provided text should be found inside the target.

    Attributes:
        uniq: The name of the operator, set to "ilike".
        predicate: The ILIKE predicate function that handles type
            casting for non-string columns.
    """

    uniq: str = field(default="ilike", init=False)

    @staticmethod
    def _predicate(column: Any, value: Any) -> Any:
        """Return the ILIKE operator for a column and value.

        Handles type casting for non-string columns to String type.
        Returns False if the column is not a SQLAlchemy column.

        Args:
            column: The SQLAlchemy column to apply the operator to.
            value: The value to match against.

        Returns:
            The ILIKE operator expression or False if column is invalid.
        """
        # op = filter_op_registry[item.op]
        if hasattr(column, "type"):
            col_type = column.type.__class__.__name__
            if col_type not in ("String",):
                column = al_cast(column, String)
        else:
            logger.warning(
                "ILIKE default implementation only works with "
                "SQLAlchemy columns. Got: %s (type: %s)",
                column,
                type(column),
            )
            return False

        return ilike_op(column, value)

    predicate: Any = field(default=_predicate)


@define
class RegexFiOp(FiOp):
    """Regular expression matching operator.

    The provided pattern should match the target using regex.

    Attributes:
        uniq: The name of the operator, set to "regex".
        predicate: The regex match predicate function.
    """

    uniq: str = field(default="regex", init=False)
    predicate: Any = field(default=regexp_match_op)


@comparison_op
@_operator_fn
def is_none(a: Any, b: Any) -> Any:
    """Check if a SQLAlchemy column expression is None.

    Args:
        a: The column expression to check.
        b: Unused parameter (required by operator interface).

    Returns:
        A SQLAlchemy comparison expression checking if a is None.
    """
    return a.is_(None)


@define
class IsNoneFiOp(FiOp):
    """Operator that checks if the target is None.

    Attributes:
        uniq: The name of the operator, set to "none".
        predicate: The is None predicate function.
    """

    uniq: str = field(default="none", init=False)
    predicate: Any = field(default=is_none)


@define
class GreaterFiOp(FiOp):
    """Greater than operator.

    The target should be larger than the value.

    Attributes:
        uniq: The name of the operator, set to "gt".
        predicate: The greater than predicate function.
    """

    uniq: str = field(default="gt", init=False)
    predicate: Any = field(default=gt)


@define
class SmallerFiOp(FiOp):
    """Less than operator.

    The target should be smaller than the value.

    Attributes:
        uniq: The name of the operator, set to "lt".
        predicate: The less than predicate function.
    """

    uniq: str = field(default="lt", init=False)
    predicate: Any = field(default=lt)


@define
class InFiOp(FiOp):
    """In operator for membership testing.

    The target needs to be one of the values.

    This can be used when the selector is simple and the `column` method
    can be used to construct the filter. For more complex cases use
    the `InExFiOp` class.

    Attributes:
        uniq: The name of the operator, set to "in".
        predicate: The in predicate function.
    """

    uniq: str = field(default="in", init=False)
    predicate: Any = field(default=in_op)


@define
class FiOpRegistry:
    """Registry for operators.

    Attributes:
        _registry: The registry of operators.
    """

    _registry: dict[str, FiOp] = field(factory=dict, repr=False)

    def __attrs_post_init__(self) -> None:
        """Initialize the registry with all operator instances and aliases.

        Registers all operator classes and their symbolic aliases (e.g.,
        "==" for "eq", ">" for "gt").
        """
        self._registry = {
            "eq": EqFiOp(),
            "not_eq": NotEqFiOp(),
            "ilike": ILikeFiOp(),
            "regex": RegexFiOp(),
            "none": IsNoneFiOp(),
            "gt": GreaterFiOp(),
            "lt": SmallerFiOp(),
            "in": InFiOp(),
        }
        self._registry["=="] = self._registry["eq"]
        self._registry["~="] = self._registry["ilike"]
        self._registry[">"] = self._registry["gt"]
        self._registry["<"] = self._registry["lt"]
        self._registry["!="] = self._registry["not_eq"]

    def __getitem__(self, key: str) -> FiOp:
        """Return the operator by name.

        Args:
            key: The name of the operator.

        Returns:
            The operator.
        """
        return self._registry[key]

    def get(self, key: str) -> Union[FiOp, None]:
        """Return the operator by name.

        Args:
            key: The name of the operator.

        Returns:
            The operator.
        """
        return self._registry.get(key, None)


filter_op_registry = FiOpRegistry()
