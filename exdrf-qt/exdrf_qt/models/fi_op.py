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
    regexp_match_op,
)


@define
class FiOp:
    """Base class for operators.

    Attributes:
        uniq: The name of the operator.
    """

    uniq: str
    predicate: Any


@define
class EqFiOp(FiOp):
    """General equality operator."""

    uniq: str = field(default="eq", init=False)
    predicate: Any = field(default=eq)


@define
class ILikeFiOp(FiOp):
    """The provided text should be found inside the target."""

    uniq: str = field(default="ilike", init=False)

    @staticmethod
    def _predicate(column: Any, value: Any) -> Any:
        """Return the ILIKE operator."""
        # op = filter_op_registry[item.op]
        if hasattr(column, "type"):
            col_type = column.type.__class__.__name__
            if col_type not in ("String",):
                column = al_cast(column, String)
        else:
            return False

        return ilike_op(column, value)

    predicate: Any = field(default=_predicate)


@define
class RegexFiOp(FiOp):
    """The provided text should be found inside the target."""

    uniq: str = field(default="regex", init=False)
    predicate: Any = field(default=regexp_match_op)


@comparison_op
@_operator_fn
def is_none(a: Any, b: Any) -> Any:
    return a.is_(None)


@define
class IsNoneFiOp(FiOp):
    """True if the target is None."""

    uniq: str = field(default="none", init=False)
    predicate: Any = field(default=is_none)


@define
class GreaterFiOp(FiOp):
    """The target should be larger than the value."""

    uniq: str = field(default="gt", init=False)
    predicate: Any = field(default=gt)


@define
class SmallerFiOp(FiOp):
    """The target should be smaller than the value."""

    uniq: str = field(default="lt", init=False)
    predicate: Any = field(default=lt)


@define
class InFiOp(FiOp):
    """The target needs to be one of the values.

    This  an be used when the selector is simple and the `column` method
    can be used to construct the filter. For more complex cases use
    the `InExFiOp` class.
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
        """Initialize the registry."""
        self._registry = {
            "eq": EqFiOp(),
            "ilike": ILikeFiOp(),
            "regex": RegexFiOp(),
            "none": IsNoneFiOp(),
            "gt": GreaterFiOp(),
            "lt": SmallerFiOp(),
            "in": InFiOp(),
        }

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
