"""Map exdrf types and Python annotations to TypeScript."""

from __future__ import annotations

import types
from typing import Any, Union, get_args, get_origin

from exdrf.constants import (
    FIELD_TYPE_BLOB,
    FIELD_TYPE_BOOL,
    FIELD_TYPE_DATE,
    FIELD_TYPE_DT,
    FIELD_TYPE_DURATION,
    FIELD_TYPE_ENUM,
    FIELD_TYPE_FILTER,
    FIELD_TYPE_FLOAT,
    FIELD_TYPE_FLOAT_LIST,
    FIELD_TYPE_FORMATTED,
    FIELD_TYPE_INT_LIST,
    FIELD_TYPE_INTEGER,
    FIELD_TYPE_REF_MANY_TO_MANY,
    FIELD_TYPE_REF_MANY_TO_ONE,
    FIELD_TYPE_REF_ONE_TO_MANY,
    FIELD_TYPE_REF_ONE_TO_ONE,
    FIELD_TYPE_SORT,
    FIELD_TYPE_STRING,
    FIELD_TYPE_STRING_LIST,
)
from exdrf_pd.visitor import ExModelVisitor

py_type_to_ts_map = {
    "str": "string",
    "int": "number",
    "float": "number",
    "bool": "boolean",
}

type_to_field_class = {
    FIELD_TYPE_BLOB: "BlobField",
    FIELD_TYPE_BOOL: "BooleanField",
    FIELD_TYPE_DATE: "DateField",
    FIELD_TYPE_DT: "DateTimeField",
    FIELD_TYPE_DURATION: "DurationField",
    FIELD_TYPE_ENUM: "EnumField",
    FIELD_TYPE_FLOAT: "FloatField",
    FIELD_TYPE_INTEGER: "IntegerField",
    FIELD_TYPE_STRING: "StringField",
    FIELD_TYPE_FORMATTED: "FormattedField",
    FIELD_TYPE_REF_ONE_TO_MANY: "RefOneToManyField",
    FIELD_TYPE_REF_MANY_TO_ONE: "RefManyToOneField",
    FIELD_TYPE_REF_ONE_TO_ONE: "RefOneToOneField",
    FIELD_TYPE_REF_MANY_TO_MANY: "RefManyToManyField",
    FIELD_TYPE_STRING_LIST: "StringListField",
    FIELD_TYPE_INT_LIST: "IntListField",
    FIELD_TYPE_FLOAT_LIST: "FloatListField",
    FIELD_TYPE_FILTER: "FilterField",
    FIELD_TYPE_SORT: "SortField",
}


def _py_type_to_ts_string(name: str) -> str:
    """Convert a stringified annotation to a TypeScript type.

    Args:
        name: Annotation text (for example ``List[str]``).

    Returns:
        Equivalent TypeScript type string.
    """

    if name == "Any":
        return "unknown"

    if name.startswith("List[") and name.endswith("]"):
        return f"{py_type_to_ts(name[5:-1])}[]"

    if name.startswith("Dict[") and name.endswith("]"):
        key, value = name[5:-1].split(", ")
        if py_type_to_ts(key) == "str":
            return f"{{ {key}: {py_type_to_ts(value)} }}"
        return f"{{ [key: {py_type_to_ts(key)}]: {py_type_to_ts(value)} }}"

    if name.startswith("Optional[") and name.endswith("]"):
        return f"{py_type_to_ts(name[9:-1])} | undefined"

    return py_type_to_ts_map.get(name, name)


def py_type_to_ts(name: Union[str, type, types.UnionType, Any]) -> str:
    """Convert a Python type or annotation string to a TypeScript type.

    Args:
        name: A type object, string annotation, or typing construct.

    Returns:
        TypeScript type text suitable for emitted source.
    """

    if isinstance(name, str):
        return _py_type_to_ts_string(name)

    args = get_args(name)
    if args and type(None) in args:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return f"{py_type_to_ts(non_none[0])} | undefined"

    origin = get_origin(name)
    if origin is list:
        if len(args) == 1:
            return f"{py_type_to_ts(args[0])}[]"

    if origin is dict:
        if len(args) == 2:
            key_t, val_t = args
            if py_type_to_ts(key_t) == "string":
                return f"{{ [key: string]: {py_type_to_ts(val_t)} }}"
            return (
                f"{{ [key: {py_type_to_ts(key_t)}]: {py_type_to_ts(val_t)} }}"
            )

    if hasattr(name, "__name__") and origin is None:
        py_name = name.__name__
        if py_name == "Any":
            return "unknown"
        mapped = py_type_to_ts_map.get(py_name)
        if mapped is not None:
            return mapped
        return py_name

    return "unknown"


def model_rel_import(model: Any, ref_model: Any) -> str:
    """Compute a model import path relative to another model.

    Args:
        model: The resource or model to import.
        ref_model: The reference model (import origin).

    Returns:
        Relative path using ``/`` segments (for TS-style paths).
    """

    categories = ExModelVisitor.category(model)
    ref_categories = ExModelVisitor.category(ref_model)

    # Find the common prefix between category chains.
    i = 0
    while (
        i < len(categories)
        and i < len(ref_categories)
        and categories[i] == ref_categories[i]
    ):
        i += 1

    # Walk up from the reference, then down through the remainder.
    path = [".."] * (len(ref_categories) - i)
    path.extend(categories[i:])

    return "/".join(path)
