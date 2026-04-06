"""Catalog of filter operators and which ``FIELD_TYPE_*`` values support them.

This module is the single source of truth for:

- **Canonical operator ids** stored in JSON filters and used by
  ``exdrf.sa_filter_op.filter_op_registry`` (for example ``eq``, ``not_eq``).
- **Surface aliases** accepted in the filter DSL or legacy payloads (for
  example ``==``, ``ne``, ``>=``).
- **Allowed operators per field type** for validators and for backend/codegen
  tools that emit OpenAPI or query parameters.

Generators (including those in application repos) can import this module and
call :func:`filter_ops_by_field_type_json` to embed the mapping in artifacts.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Dict, Final, FrozenSet, Mapping, Optional

from exdrf.constants import (
    FIELD_TYPE_BLOB,
    FIELD_TYPE_BOOL,
    FIELD_TYPE_DATE,
    FIELD_TYPE_DT,
    FIELD_TYPE_DURATION,
    FIELD_TYPE_ENUM,
    FIELD_TYPE_FLOAT,
    FIELD_TYPE_FLOAT_LIST,
    FIELD_TYPE_FORMATTED,
    FIELD_TYPE_INT_LIST,
    FIELD_TYPE_INTEGER,
    FIELD_TYPE_REF_MANY_TO_MANY,
    FIELD_TYPE_REF_MANY_TO_ONE,
    FIELD_TYPE_REF_ONE_TO_MANY,
    FIELD_TYPE_REF_ONE_TO_ONE,
    FIELD_TYPE_STRING,
    FIELD_TYPE_STRING_LIST,
    FIELD_TYPE_TIME,
)

# Canonical ids match ``FiOp.uniq`` / keys in ``FiOpRegistry`` (exdrf-qt).
FILTER_OP_EQ: Final = "eq"
FILTER_OP_NOT_EQ: Final = "not_eq"
FILTER_OP_ILIKE: Final = "ilike"
FILTER_OP_REGEX: Final = "regex"
FILTER_OP_NONE: Final = "none"
FILTER_OP_GT: Final = "gt"
FILTER_OP_LT: Final = "lt"
FILTER_OP_GE: Final = "ge"
FILTER_OP_LE: Final = "le"
FILTER_OP_IN: Final = "in"

# All canonical operators known to the SQLAlchemy-backed registry.
ALL_CANONICAL_FILTER_OPS: Final[FrozenSet[str]] = frozenset(
    {
        FILTER_OP_EQ,
        FILTER_OP_NOT_EQ,
        FILTER_OP_ILIKE,
        FILTER_OP_REGEX,
        FILTER_OP_NONE,
        FILTER_OP_GT,
        FILTER_OP_LT,
        FILTER_OP_GE,
        FILTER_OP_LE,
        FILTER_OP_IN,
    }
)

# Comparison and membership operators (no pattern match).
_ORDER_AND_MEMBERSHIP_OPS: Final[FrozenSet[str]] = frozenset(
    {
        FILTER_OP_EQ,
        FILTER_OP_NOT_EQ,
        FILTER_OP_GT,
        FILTER_OP_LT,
        FILTER_OP_GE,
        FILTER_OP_LE,
        FILTER_OP_IN,
        FILTER_OP_NONE,
    }
)

# String-oriented column types: pattern match plus ordering.
_STRING_LIKE_OPS: Final[FrozenSet[str]] = frozenset(
    _ORDER_AND_MEMBERSHIP_OPS | {FILTER_OP_ILIKE, FILTER_OP_REGEX}
)

# Map exdrf ``type_name`` -> allowed **canonical** operator ids.
_FILTER_OPS_BY_FIELD_TYPE: Dict[str, FrozenSet[str]] = {
    FIELD_TYPE_STRING: _STRING_LIKE_OPS,
    FIELD_TYPE_FORMATTED: _STRING_LIKE_OPS,
    FIELD_TYPE_INTEGER: _ORDER_AND_MEMBERSHIP_OPS,
    FIELD_TYPE_FLOAT: _ORDER_AND_MEMBERSHIP_OPS,
    FIELD_TYPE_BOOL: frozenset(
        {FILTER_OP_EQ, FILTER_OP_NOT_EQ, FILTER_OP_NONE}
    ),
    FIELD_TYPE_DATE: _ORDER_AND_MEMBERSHIP_OPS,
    FIELD_TYPE_DT: _ORDER_AND_MEMBERSHIP_OPS,
    FIELD_TYPE_TIME: _ORDER_AND_MEMBERSHIP_OPS,
    FIELD_TYPE_DURATION: _ORDER_AND_MEMBERSHIP_OPS,
    FIELD_TYPE_ENUM: frozenset(
        {FILTER_OP_EQ, FILTER_OP_NOT_EQ, FILTER_OP_IN, FILTER_OP_NONE}
    ),
    FIELD_TYPE_BLOB: frozenset(
        {FILTER_OP_EQ, FILTER_OP_NOT_EQ, FILTER_OP_NONE}
    ),
    FIELD_TYPE_STRING_LIST: frozenset(
        {FILTER_OP_EQ, FILTER_OP_NOT_EQ, FILTER_OP_IN, FILTER_OP_NONE}
    ),
    FIELD_TYPE_INT_LIST: frozenset(
        {FILTER_OP_EQ, FILTER_OP_NOT_EQ, FILTER_OP_IN, FILTER_OP_NONE}
    ),
    FIELD_TYPE_FLOAT_LIST: frozenset(
        {FILTER_OP_EQ, FILTER_OP_NOT_EQ, FILTER_OP_IN, FILTER_OP_NONE}
    ),
    FIELD_TYPE_REF_MANY_TO_ONE: _ORDER_AND_MEMBERSHIP_OPS,
    FIELD_TYPE_REF_ONE_TO_ONE: _ORDER_AND_MEMBERSHIP_OPS,
    FIELD_TYPE_REF_ONE_TO_MANY: _ORDER_AND_MEMBERSHIP_OPS,
    FIELD_TYPE_REF_MANY_TO_MANY: _ORDER_AND_MEMBERSHIP_OPS,
}

FILTER_OPS_BY_FIELD_TYPE: Final[Mapping[str, FrozenSet[str]]] = (
    MappingProxyType(_FILTER_OPS_BY_FIELD_TYPE)
)

# Every surface form maps to exactly one canonical id.
_FILTER_OP_ALIASES: Dict[str, str] = {
    # Canonical forms (identity).
    FILTER_OP_EQ: FILTER_OP_EQ,
    FILTER_OP_NOT_EQ: FILTER_OP_NOT_EQ,
    FILTER_OP_ILIKE: FILTER_OP_ILIKE,
    FILTER_OP_REGEX: FILTER_OP_REGEX,
    FILTER_OP_NONE: FILTER_OP_NONE,
    FILTER_OP_GT: FILTER_OP_GT,
    FILTER_OP_LT: FILTER_OP_LT,
    FILTER_OP_GE: FILTER_OP_GE,
    FILTER_OP_LE: FILTER_OP_LE,
    FILTER_OP_IN: FILTER_OP_IN,
    # JSON / docs sometimes use ``ne`` instead of ``not_eq``.
    "ne": FILTER_OP_NOT_EQ,
    # Filter DSL symbolic tokens (see ``Tokenizer`` in ``filter_dsl``).
    "==": FILTER_OP_EQ,
    "!=": FILTER_OP_NOT_EQ,
    ">": FILTER_OP_GT,
    "<": FILTER_OP_LT,
    ">=": FILTER_OP_GE,
    "<=": FILTER_OP_LE,
    # Historical / alternate spellings.
    "gte": FILTER_OP_GE,
    "lte": FILTER_OP_LE,
    "~=": FILTER_OP_ILIKE,
}

FILTER_OP_ALIASES: Final[Mapping[str, str]] = MappingProxyType(
    _FILTER_OP_ALIASES
)


def normalize_filter_op(op: str) -> Optional[str]:
    """Resolve a filter operator string to its canonical id.

    Matching is case-insensitive for the lookup key.

    Args:
        op: Operator as provided by JSON, the DSL, or another client.

    Returns:
        Canonical operator id, or ``None`` if the string is not recognized.
    """
    if not op:
        return None
    return _FILTER_OP_ALIASES.get(op.lower())


def canonical_filter_ops_for_type(type_name: str) -> FrozenSet[str]:
    """Return the canonical operators allowed for an exdrf ``type_name``.

    Unknown ``type_name`` values fall back to :data:`ALL_CANONICAL_FILTER_OPS`
    so custom field types remain usable until they register a mapping.

    Args:
        type_name: Value of :attr:`exdrf.field.ExField.type_name`.

    Returns:
        Frozen set of canonical operator ids.
    """
    mapped = _FILTER_OPS_BY_FIELD_TYPE.get(type_name)
    if mapped is not None:
        return mapped
    return ALL_CANONICAL_FILTER_OPS


def filter_op_allowed_for_type(type_name: str, op: str) -> bool:
    """Return whether ``op`` is allowed for the given field ``type_name``.

    Args:
        type_name: Field ``type_name`` from metadata.
        op: Operator in any supported surface form.

    Returns:
        ``True`` if the operator is known and allowed for that type.
    """
    canon = normalize_filter_op(op)
    if canon is None:
        return False
    return canon in canonical_filter_ops_for_type(type_name)


def filter_ops_by_field_type_json() -> Dict[str, list[str]]:
    """Build a JSON-friendly ``type_name -> [canonical_op, ...]`` mapping.

    Returns:
        Dict suitable for ``json.dumps`` or embedding in generated code.
    """
    result: Dict[str, list[str]] = {}
    for type_name, ops in _FILTER_OPS_BY_FIELD_TYPE.items():
        result[type_name] = sorted(ops)
    return result


def filter_op_alias_map_json() -> Dict[str, str]:
    """Return ``alias -> canonical`` as plain strings for generators.

    Returns:
        Dict of every alias (lowercase keys) to canonical operator id.
    """
    return dict(_FILTER_OP_ALIASES)
