"""Build static ``get_def`` field dictionaries from ``ExField`` metadata.

``exdrf-gen-al2rcv`` calls into this module while rendering
``resource_rcv_paths.py.j2``. Each emitted dict matches the discriminated
``RcvField`` union in ``exdrf_rcv.models`` so generated modules validate at
import time and ``resolve_rcv_plan`` can parse them without extra transforms.

The mapping uses ``ExField.field_properties(explicit=True)`` as the single
source of field metadata, then splits keys between top-level RCV wire fields
(``name``, ``kind``, ``required``, shared flags) and the nested ``data``
object according to ``FIELD_TYPE_*`` in ``exdrf.constants``.
"""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any, Final, Mapping

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
    FIELD_TYPE_TIME,
)
from exdrf_rcv.models import RcvField
from pydantic import TypeAdapter

if TYPE_CHECKING:
    from exdrf.field import ExField
    from exdrf.resource import ExResource


# Keys copied from ``field_properties(explicit=True)`` onto the RCV field dict
# root (alongside ``name``, ``kind``, ``required``), when present and
# non-``None``.
_BASE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "title",
        "description",
        "category",
        "pos_hint",
        "primary",
        "visible",
        "read_only",
        "nullable",
        "sortable",
        "filterable",
        "exportable",
        "qsearch",
        "resizable",
        "derived",
    }
)

# Per ``FIELD_TYPE_*``, which property names from ``field_properties`` belong
# under ``data`` (everything else stays on the root or is dropped).
_KIND_DATA_KEYS: Final[Mapping[str, frozenset[str]]] = {
    FIELD_TYPE_BLOB: frozenset({"mime_type"}),
    FIELD_TYPE_BOOL: frozenset({"true_str", "false_str"}),
    FIELD_TYPE_STRING: frozenset(
        {
            "multiline",
            "min_length",
            "max_length",
            "enum_values",
            "no_dia_field",
        },
    ),
    FIELD_TYPE_STRING_LIST: frozenset(
        {
            "multiline",
            "min_length",
            "max_length",
            "enum_values",
            "no_dia_field",
        },
    ),
    FIELD_TYPE_FORMATTED: frozenset(
        {
            "multiline",
            "min_length",
            "max_length",
            "enum_values",
            "no_dia_field",
            "format",
        },
    ),
    FIELD_TYPE_INTEGER: frozenset(
        {"min", "max", "unit", "unit_symbol", "enum_values"},
    ),
    FIELD_TYPE_INT_LIST: frozenset(
        {"min", "max", "unit", "unit_symbol", "enum_values"},
    ),
    FIELD_TYPE_FLOAT: frozenset(
        {
            "min",
            "max",
            "precision",
            "scale",
            "unit",
            "unit_symbol",
            "enum_values",
        },
    ),
    FIELD_TYPE_FLOAT_LIST: frozenset(
        {
            "min",
            "max",
            "precision",
            "scale",
            "unit",
            "unit_symbol",
            "enum_values",
        },
    ),
    FIELD_TYPE_DATE: frozenset({"min", "max", "format"}),
    FIELD_TYPE_DT: frozenset({"min", "max", "format"}),
    FIELD_TYPE_TIME: frozenset({"min", "max", "format"}),
    FIELD_TYPE_DURATION: frozenset({"min", "max"}),
    FIELD_TYPE_ENUM: frozenset({"enum_values"}),
    FIELD_TYPE_REF_ONE_TO_MANY: frozenset(
        {
            "ref",
            "direction",
            "subordinate",
            "expect_lots",
            "provides",
            "depends_on",
            "bridge",
        },
    ),
    FIELD_TYPE_REF_ONE_TO_ONE: frozenset(
        {
            "ref",
            "direction",
            "subordinate",
            "expect_lots",
            "provides",
            "depends_on",
            "bridge",
        },
    ),
    FIELD_TYPE_REF_MANY_TO_MANY: frozenset(
        {
            "ref",
            "direction",
            "subordinate",
            "expect_lots",
            "provides",
            "depends_on",
            "bridge",
            "ref_intermediate",
        },
    ),
    FIELD_TYPE_REF_MANY_TO_ONE: frozenset(
        {
            "ref",
            "direction",
            "subordinate",
            "expect_lots",
            "provides",
            "depends_on",
            "bridge",
        },
    ),
    FIELD_TYPE_FILTER: frozenset(),
    FIELD_TYPE_SORT: frozenset(),
}


# Shared adapter used for fail-fast validation during generation and in tests.
_rcv_field_adapter = TypeAdapter(RcvField)


def _normalize_enum_values_for_rcv_enum(raw: Any) -> list[str]:
    """Convert exdrf enum wire shapes into ``RcvEnumFieldData.enum_values``.

    ``EnumField`` may expose ``enum_values`` as a list of ``(value, label)``
    tuples, while ``RcvEnumFieldData`` expects a flat list of allowed string
    values. Other list shapes are stringified element-wise.

    Args:
        raw: Value taken from ``field_properties`` for ``enum_values``.

    Returns:
        List of allowed enum values as strings, never ``None``.
    """

    if raw is None:
        return []

    # Tuple list: take the wire value (first element of each pair).
    if isinstance(raw, list) and raw and isinstance(raw[0], tuple):
        return [str(t[0]) for t in raw]

    # Already a list of scalars.
    if isinstance(raw, list):
        return [str(x) for x in raw]

    return []


def _normalize_depends_on(raw: Any) -> list[tuple[str, str]]:
    """Coerce relation ``depends_on`` metadata into ``(concept, target)`` pairs.

    ``RcvRefFieldData.depends_on`` is a list of two-string tuples. Exdrf may
    emit tuples, or legacy string entries using ``concept:target`` syntax.

    Args:
        raw: ``depends_on`` list from ``field_properties`` or similar.

    Returns:
        Normalized dependency pairs; empty when ``raw`` is falsy or unusable.
    """

    if not raw:
        return []

    out: list[tuple[str, str]] = []

    # Walk list entries, accepting 2-tuples or ``"concept:target"`` strings.
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, tuple) and len(item) == 2:
                out.append((str(item[0]), str(item[1])))
            elif isinstance(item, str) and ":" in item:
                a, b = item.split(":", maxsplit=1)
                out.append((a.strip(), b.strip()))
    return out


def _resource_name_from_value(value: Any) -> str | None:
    """Turn an ``ExResource`` instance (or similar) into a stable resource name.

    ``field_properties`` sometimes returns resource objects for ``ref`` or
    ``bridge`` instead of pre-serialized names. This helper reads ``.name`` when
    available so emitted Python literals stay plain strings.

    Args:
        value: Arbitrary value from ``field_properties``.

    Returns:
        Wire string name, or ``None`` when ``value`` is ``None``.
    """

    if value is None:
        return None
    name = getattr(value, "name", None)
    if isinstance(name, str):
        return name
    return str(value)


def ex_field_to_rcv_field_dict(field: "ExField") -> dict[str, Any]:
    """Map one ``ExField`` to a discriminated ``RcvField`` wire dict.

    Reads ``field.field_properties(explicit=True)``, copies shared metadata onto
    the dict root, fills ``data`` with only keys allowed for that
    ``FIELD_TYPE_*``, and applies small normalizations (enum values, relation
    ``depends_on``, M2M ``ref_intermediate`` → ``bridge``, mandatory ``ref``).

    Args:
        field: Dataset field to describe.

    Returns:
        Mapping suitable for ``TypeAdapter(RcvField).validate_python``.

    Raises:
        ValueError: If ``type_name`` is not supported or a relation lacks
            ``ref``.
    """

    # Pull the full exdrf property bag so list and relation attrs are present.
    full = field.field_properties(explicit=True)
    kind = str(full["type_name"])

    # Every supported wire ``kind`` must appear in the data-key table.
    if kind not in _KIND_DATA_KEYS:
        raise ValueError(
            "Unsupported field type_name %r for resource %s field %s."
            % (kind, full.get("resource"), full.get("name")),
        )

    # Root keys always include identity, wire kind, and a simple required rule.
    out: dict[str, Any] = {
        "name": str(full["name"]),
        "kind": kind,
        "required": not bool(full.get("nullable", True)),
    }

    # Optional presentation and behavior flags shared across field kinds.
    for key in _BASE_KEYS:
        if key not in full:
            continue
        val = full[key]
        if val is None:
            continue
        out[key] = val

    # Type-specific payload: only whitelisted keys from ``full`` go into data.
    allowed = _KIND_DATA_KEYS[kind]
    data: dict[str, Any] = {}
    for key in allowed:
        if key == "ref_intermediate":
            continue
        if key not in full:
            continue
        val = full[key]
        if val is None:
            continue

        # ``ref`` / ``bridge`` may be ``ExResource`` objects; coerce to names.
        if key in ("ref", "bridge") and not isinstance(val, str):
            wire = _resource_name_from_value(val)
            if wire is not None:
                data[key] = wire
            continue

        data[key] = val

    # Many-to-many uses ``ref_intermediate`` in exdrf; RCV exposes it as bridge.
    if "ref_intermediate" in full and full["ref_intermediate"] is not None:
        bridge = _resource_name_from_value(full["ref_intermediate"])
        if bridge is not None:
            data["bridge"] = bridge

    # Wire enum field uses plain strings; exdrf may still emit tuple pairs.
    if kind == FIELD_TYPE_ENUM:
        data["enum_values"] = _normalize_enum_values_for_rcv_enum(
            data.get("enum_values", full.get("enum_values")),
        )

    # Relation kinds must always expose ``data.ref``; fill from related resource
    # when the property bag did not already include a string ``ref``.
    if kind in (
        FIELD_TYPE_REF_ONE_TO_MANY,
        FIELD_TYPE_REF_ONE_TO_ONE,
        FIELD_TYPE_REF_MANY_TO_MANY,
        FIELD_TYPE_REF_MANY_TO_ONE,
    ):
        if "ref" not in data:
            rel = field.related_resource
            if rel is None:
                raise ValueError(
                    "Relation field %s.%s missing ref target."
                    % (full.get("resource"), full.get("name")),
                )
            data["ref"] = rel.name
        if "depends_on" in data:
            data["depends_on"] = _normalize_depends_on(data.get("depends_on"))

    # Attach nested ``data`` for Pydantic discriminated validation.
    out["data"] = data
    return out


def build_rcv_field_dicts_for_resource(
    resource: "ExResource",
) -> list[dict[str, Any]]:
    """Build and validate RCV field dicts for every sorted field on a resource.

    Iterates ``resource.sorted_fields`` (the same ordering exdrf uses
    elsewhere), converts each field with :func:`ex_field_to_rcv_field_dict`,
    and validates with the same ``TypeAdapter(RcvField)`` used at runtime so
    codegen fails immediately when a field cannot be expressed in the RCV wire
    schema.

    Args:
        resource: ``ExResource`` from the SQLAlchemy-backed dataset.

    Returns:
        List of wire dicts accepted by ``RcvField``.

    Raises:
        ValueError: Propagated from :func:`ex_field_to_rcv_field_dict` or
            Pydantic when a field dict is invalid.
    """

    result: list[dict[str, Any]] = []

    # One dict per field; validation mirrors ``resolve_rcv_plan`` parsing.
    for fld in resource.sorted_fields:
        dct = ex_field_to_rcv_field_dict(fld)
        _rcv_field_adapter.validate_python(dct)
        result.append(dct)
    return result


def _norm_for_repr(value: Any) -> Any:
    """Recursively normalize values before ``repr`` for generated Python source.

    ``datetime`` / ``date`` / ``time`` objects would otherwise render as
    ``datetime.date(...)`` calls that require imports in every generated file.
    ISO strings keep emitted modules free of datetime imports while remaining
    JSON-compatible when plans are serialized. Dicts, lists, and tuples are
    walked depth-first; other scalars are returned unchanged.

    Args:
        value: Any nested structure taken from field dicts.

    Returns:
        Structure of the same shape with date-like leaves replaced by strings.
    """

    # Datetime instances include date-only when typed as datetime; normalize.
    if isinstance(value, datetime.datetime):
        return value.isoformat()

    # Calendar dates without time-of-day.
    if isinstance(value, datetime.date):
        return value.isoformat()

    # Time-of-day without calendar component.
    if isinstance(value, datetime.time):
        return value.isoformat()

    # Recurse into mapping values while preserving key objects.
    if isinstance(value, dict):
        return {k: _norm_for_repr(v) for k, v in value.items()}

    # Preserve list ordering.
    if isinstance(value, list):
        return [_norm_for_repr(v) for v in value]

    # Preserve tuple type (e.g. ``enum_values`` pairs).
    if isinstance(value, tuple):
        return tuple(_norm_for_repr(v) for v in value)

    return value


def rcv_field_dicts_py_literal(rows: list[dict[str, Any]]) -> str:
    """Render ``rows`` as a Python literal expression for Jinja substitution.

    The template embeds the result as ``return <this>`` inside ``get_def``.
    Values are normalized via :func:`_norm_for_repr` then passed to ``repr``,
    which yields valid Python for dicts, lists, tuples, strings, numbers, and
    booleans suitable for static analysis and runtime ``eval``-free import.

    Args:
        rows: Field dicts; may contain ``date`` / ``datetime`` / ``time``
            leaves.

    Returns:
        Single-line (or multi-line) source fragment, typically starting with
        ``[`` for a list literal.
    """

    return repr(_norm_for_repr(rows))


def default_rcv_render_type() -> str:
    """Return the default ``RCV_RENDER_TYPE`` string emitted beside ``get_def``.

    Until resource-level render metadata exists, every generated module uses
    this constant so ``resolve_rcv_plan`` always receives a non-empty
    ``render_type`` when the template does not override it.

    Returns:
        Fixed string ``"default"``.
    """

    return "default"


def validate_rcv_field_dicts(rows: list[dict[str, Any]]) -> None:
    """Validate each wire dict using the same ``RcvField`` adapter as
    production code.

    Intended for unit tests and CI checks on hand-built or captured dict lists
    without running the full generator.

    Args:
        rows: Candidate field mappings (each must match one ``RcvField``).

    Raises:
        pydantic.ValidationError: When any row fails discriminated validation.
    """

    for row in rows:
        _rcv_field_adapter.validate_python(row)
