"""Build al2pd Jinja context: Pydantic types and field partitions from exdrf."""

from __future__ import annotations

import json
import re
import textwrap
from dataclasses import dataclass
from typing import Any, List, Sequence, Tuple, cast

from exdrf.constants import FIELD_TYPE_DURATION
from exdrf.field import ExField
from exdrf.field_types.blob_field import BlobField
from exdrf.field_types.bool_field import BoolField
from exdrf.field_types.date_field import DateField
from exdrf.field_types.date_time import DateTimeField
from exdrf.field_types.enum_field import EnumField
from exdrf.field_types.float_field import FloatField
from exdrf.field_types.float_list import FloatListField
from exdrf.field_types.formatted import FormattedField
from exdrf.field_types.int_field import IntField
from exdrf.field_types.int_list import IntListField
from exdrf.field_types.ref_base import RefBaseField
from exdrf.field_types.str_field import StrField
from exdrf.field_types.str_list import StrListField
from exdrf.field_types.time_field import TimeField
from exdrf_pd.schema_extra import wrap_exdrf_props

from exdrf_gen_al2pd.field_partition import (
    depends_on_fk_field_names,
    format_db2m_class_doc_body,
    optionalize,
    partition_fields,
)

# Module tuning: audit columns, flake8 width, and description-line budgets for
# emitted ``Field(...)`` and class docstrings.

# Audit columns excluded from Create/Edit payloads.
_AUDIT_FIELD_NAMES = frozenset({"created_on", "updated_on"})

# Keys omitted from ``json_schema_extra["exdrf"]`` blobs (redundant with the
# surrounding Pydantic field: ``description=``, optional/required annotation,
# or the model class docstring for resource-level metadata).
_AL2PD_EXDRF_REDUNDANT_KEYS = frozenset(
    {"title", "name", "resource", "type_name", "description", "nullable"},
)


# Match ``max-line-length`` in repo ``.flake8`` / package ``pyproject.toml``
# (generated ``Field`` and docstring lines must fit).
_DB2M_MAX_LINE = 80

# ``format_db2m_class_doc_body`` indents each logical doc line by four spaces.
_DB2M_DOC_LOGICAL_MAX = _DB2M_MAX_LINE - 4

# ``interface.py.j2`` emits ``        description=<literal><extra...>,``.
_FIELD_DESCRIPTION_LINE_PREFIX_LEN = len("        description=")

# ``interface.py.j2`` emits ``        json_schema_extra=<dict literal>,``.
_FIELD_JSON_SCHEMA_EXTRA_PREFIX_LEN = len("        json_schema_extra=")


def _strip_al2pd_exdrf_redundant(props: dict) -> dict:
    """Remove metadata keys that duplicate generated Pydantic declarations."""

    for key in _AL2PD_EXDRF_REDUNDANT_KEYS:
        props.pop(key, None)
    return props


# Stable module-level names for module-level ``json_schema_extra`` / model
# config dict assignments.


def _exdrf_resource_var(model_name: str) -> str:
    """Stable module symbol for a resource ``model_config`` payload."""
    return f"_EXDRF_RES_{model_name}"


def _py_inline_atom(value: Any) -> str:
    """Single-line Python literal for a scalar (no dict/list)."""

    if value is None:
        return "None"
    if value is True:
        return "True"
    if value is False:
        return "False"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    return json.dumps(str(value), ensure_ascii=False)


def _py_inline_value(value: Any) -> str:
    """Compact one-line Python literal for any supported exdrf value."""

    if isinstance(value, dict):
        if not value:
            return "{}"
        inner = ", ".join(
            f"{json.dumps(k, ensure_ascii=False)}: {_py_inline_value(v)}"
            for k, v in value.items()
        )
        return "{" + inner + "}"
    if isinstance(value, list):
        if not value:
            return "[]"
        return "[" + ", ".join(_py_inline_value(v) for v in value) + "]"
    return _py_inline_atom(value)


def _split_long_string_literal(lit: str, ind: str, width: int) -> List[str]:
    """Break a double-quoted string across lines (implicit concatenation)."""

    if len(ind) + len(lit) <= width:
        return [ind + lit]
    if not (lit.startswith('"') and lit.endswith('"')):
        return [ind + lit]

    inner = lit[1:-1]
    pad = ind + "    "
    max_piece = max(4, width - len(pad))
    parts: List[str] = []
    i = 0
    n = len(inner)
    while i < n:
        lo = i + 1
        hi = n
        best = i + 1
        while lo <= hi:
            mid = (lo + hi) // 2
            piece = json.dumps(inner[i:mid], ensure_ascii=False)
            if len(piece) <= max_piece:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        if best <= i:
            best = i + 1
        if best < n:
            while best > i and inner[best - 1] == "\\":
                best -= 1
            if best <= i:
                best = i + 1
        parts.append(json.dumps(inner[i:best], ensure_ascii=False))
        i = best
    if len(parts) == 1:
        return [pad + parts[0]]
    out = [ind + "("]
    for p in parts:
        out.append(pad + p)
    out.append(ind + ")")
    return out


def _emit_exdrf_lines(value: Any, indent: str, width: int) -> List[str]:
    """Multi-line dict/list literal; each physical line length <= ``width``."""

    step = "    "
    child = indent + step

    if isinstance(value, dict):
        if not value:
            return [indent + "{}"]
        one = _py_inline_value(value)
        if len(indent) + len(one) <= width:
            return [indent + one]
        out: List[str] = [indent + "{"]
        items = list(value.items())
        for idx, (k, v) in enumerate(items):
            trail = "," if idx < len(items) - 1 else ""
            ks = json.dumps(k, ensure_ascii=False)
            if isinstance(v, (dict, list)):
                nest = _emit_exdrf_lines(v, child + step, width)
                head = nest[0].lstrip()
                line = f"{child}{ks}: {head}"
                if len(line) > width:
                    line = f"{child}{ks}:"
                    out.append(line)
                    out.extend(nest)
                else:
                    out.append(line)
                    out.extend(nest[1:])
                out[-1] = out[-1] + trail
            else:
                lit = _py_inline_atom(v)
                line = f"{child}{ks}: {lit}{trail}"
                if len(line) <= width:
                    out.append(line)
                else:
                    out.append(f"{child}{ks}:")
                    out.extend(
                        _split_long_string_literal(lit, child + step, width)
                    )
                    out[-1] = out[-1] + trail
        out.append(indent + "}")
        return out

    if isinstance(value, list):
        if not value:
            return [indent + "[]"]
        one = _py_inline_value(value)
        if len(indent) + len(one) <= width:
            return [indent + one]
        out = [indent + "["]
        for idx, item in enumerate(value):
            trail = "," if idx < len(value) - 1 else ""
            if isinstance(item, (dict, list)):
                nest = _emit_exdrf_lines(item, child, width)
                if len(nest) == 1:
                    out.append(nest[0] + trail)
                else:
                    out.append(nest[0])
                    out.extend(nest[1:-1])
                    out.append(nest[-1] + trail)
            else:
                lit = _py_inline_atom(item)
                line = f"{child}{lit}{trail}"
                if len(line) <= width:
                    out.append(line)
                else:
                    out.extend(_split_long_string_literal(lit, child, width))
                    out[-1] = out[-1] + trail
        out.append(indent + "]")
        return out

    line = indent + _py_inline_atom(value)
    if len(line) <= width:
        return [line]
    return _split_long_string_literal(_py_inline_atom(value), indent, width)


def _exdrf_dict_rhs(props: dict, *, assignee: str) -> str:
    """Emit a wrapped exdrf dict as a Python literal (no ``json.loads``).

    Args:
        props: Field or resource properties (JSON-serializable).
        assignee: Module-level LHS name (used for one-line width check).

    Returns:
        Source for the right-hand side of the assignment.
    """

    wrapped = wrap_exdrf_props(props)
    one_line = _py_inline_value(wrapped)
    if len(f"{assignee} = {one_line}") <= _DB2M_MAX_LINE:
        return one_line

    lines = _emit_exdrf_lines(wrapped, "", _DB2M_MAX_LINE)
    return "\n".join(lines)


def _exdrf_json_schema_extra_expr(props: dict) -> str:
    """Source for ``json_schema_extra=`` inside a ``Field(...)`` call.

    Args:
        props: Stripped field exdrf properties (before ``wrap_exdrf_props``).

    Returns:
        Dict literal (one line or multi-line); each output line fits flake8
        width when placed after ``        json_schema_extra=``.
    """

    wrapped = wrap_exdrf_props(props)
    one_line = _py_inline_value(wrapped)
    if (
        _FIELD_JSON_SCHEMA_EXTRA_PREFIX_LEN + len(one_line) + 1
        <= _DB2M_MAX_LINE
    ):
        return one_line

    cont_indent = "        "
    inner_w = _DB2M_MAX_LINE - len(cont_indent)
    last_lines: List[str] = [one_line]
    while inner_w >= 8:
        block = "\n".join(_emit_exdrf_lines(wrapped, "", inner_w))
        last_lines = block.split("\n")
        if len(last_lines) > 1:
            return (
                last_lines[0]
                + "\n"
                + "\n".join(cont_indent + ln for ln in last_lines[1:])
            )
        if (
            _FIELD_JSON_SCHEMA_EXTRA_PREFIX_LEN + len(last_lines[0]) + 1
            <= _DB2M_MAX_LINE
        ):
            return last_lines[0]
        inner_w -= 8
    return (
        last_lines[0]
        + "\n"
        + "\n".join(cont_indent + ln for ln in last_lines[1:])
    )


# Strip common type-leading noise from column/field descriptions so attribute
# lines stay ``name: prose`` without redundant type hints.
_DESC_TYPE_PREFIX = re.compile(
    r"^("
    r"`[^`]+`(?:\s*,\s*`[^`]+`)*(?:\s+or\s+`[^`]+`)?\s*[—:–-]\s*"
    r"|(?:Optional|Mapped|List|Dict|Iterable)\[[^\]]+\]\s*[.:]\s*"
    r")",
)


def model_summary_one_line(model: Any) -> str:
    """First line of the resource description, or a short title fallback.

    Args:
        model: Dataset resource (``description``, ``text_name``, ``name``).

    Returns:
        A single-line summary for the class docstring.
    """

    # Prefer the first paragraph / first line of the resource description.
    desc = (getattr(model, "description", None) or "").strip()
    if desc:

        # Strip trailing paragraphs and take the first physical line only.
        head = desc.split("\n\n", 1)[0]
        first = head.split("\n", 1)[0].strip()
        if first:
            return first

    # Fall back to UI text name or a generic label.
    text_name = getattr(model, "text_name", None)
    if text_name:
        return str(text_name).strip()
    return f"{getattr(model, 'name', 'Model')} record."


def clean_attribute_description(field: ExField) -> str:
    """Build one-line attribute prose without leading type artifacts.

    Args:
        field: exdrf field (scalar or relation).

    Returns:
        Text after ``name:`` in the Google-style Attributes block.
    """

    # Derive prose from description, title, or a humanized field name.
    raw = (field.description or "").strip()
    if not raw:
        raw = (field.title or "").strip()
    if not raw:
        raw = field.name.replace("_", " ")

    # Strip leading type noise so attribute lines read as ``name: prose``.
    one_line = " ".join(raw.split())
    stripped = _DESC_TYPE_PREFIX.sub("", one_line, count=1).strip()
    return stripped or field.name.replace("_", " ")


def _wrap_summary_lines(
    text: str,
    width: int = _DB2M_DOC_LOGICAL_MAX,
) -> List[str]:
    """Split a long class summary across multiple doc lines.

    Args:
        text: Summary text (already stripped).
        width: Maximum characters per wrapped segment before the doc formatter
            adds its four-space indent.

    Returns:
        One or more lines to place at the start of the class docstring.
    """

    # Short summaries stay one line; long ones wrap within the doc budget.
    if len(text) <= width:
        return [text]
    return textwrap.wrap(
        text,
        width=width,
        break_long_words=True,
        break_on_hyphens=True,
    )


def _google_attribute_wrapped_lines(
    name: str,
    prose: str,
    max_width: int = _DB2M_DOC_LOGICAL_MAX,
) -> List[str]:
    """Build wrapped ``name: prose`` lines for the Attributes block.

    Args:
        name: Field name.
        prose: Attribute description (no type).
        max_width: Maximum length of each logical line (including this
            block's own four-space indent); ``format_db2m_class_doc_body``
            prepends another four spaces.

    Returns:
        Logical lines (each starts with four spaces, then ``name:`` or
            eight spaces for continuations).
    """

    # First line is ``    name: `` plus as much prose as fits; wraps indent.
    prefix = f"    {name}: "
    prose_one = " ".join(prose.split())
    if len(prefix) + len(prose_one) <= max_width:
        return [prefix + prose_one]

    # Wrap the prose body; continuation lines are eight-space indented only.
    body_w = max(20, max_width - len(prefix))
    body_lines = textwrap.wrap(
        prose_one,
        width=body_w,
        break_long_words=True,
        break_on_hyphens=True,
    )
    if not body_lines:
        return [prefix.rstrip()]
    out: List[str] = [prefix + body_lines[0]]
    cont = " " * 8

    # Attribute continuations align under the prose column after ``name:``.
    for ln in body_lines[1:]:
        out.append(cont + ln)
    return out


def build_google_db2m_class_doc_body(
    summary: str,
    fields: Sequence[ExField],
    fallback_summary: str,
) -> str:
    """Google-style class docstring body for emitted Pydantic fields.

    Args:
        summary: One-line class summary.
        fields: Fields to list under ``Attributes:`` (in order).
        fallback_summary: Used when ``summary`` is empty after strip.

    Returns:
        Indented body for ``interface.py.j2`` (via
        :func:`format_db2m_class_doc_body`).
    """

    # Summary lines, then optional Google ``Attributes`` block for each field.
    sum_line = (summary or "").strip() or fallback_summary
    lines: List[str] = list(_wrap_summary_lines(sum_line))
    if fields:

        # Blank line, ``Attributes:`` header, blank line, then each field block.
        lines.append("")
        lines.append("Attributes:")
        lines.append("")
        for fld in fields:
            lines.extend(
                _google_attribute_wrapped_lines(
                    fld.name,
                    clean_attribute_description(fld),
                )
            )

    # Indent and normalize blank lines for the Jinja class docstring slot.
    return format_db2m_class_doc_body(lines, fallback_summary)


# Frozen specs bundle everything ``interface.py.j2`` needs for one emitted field
# line (scalar, relation, or payload list).


@dataclass(frozen=True)
class Db2mScalarFieldSpec:
    """One scalar field line for generated Pydantic output.

    Attributes:
        name: Python attribute name (matches the ORM column / field name).
        annotation: Full type annotation including ``| None`` when nullable.
        title: Human-readable title for ``Field(title=...)``.
        doc_lines: Description split into lines (for class docstrings only).
        default_value: First positional argument to ``Field``
            (``...`` or ``None``).
        description_literal: Python string literal (possibly parenthesized
            implicit concat) for ``Field(description=...)``.
        extra_field_args: Additional keyword args as source text, e.g.
            ``, max_length=255``.
        json_schema_extra_expr: Dict literal for ``Field(json_schema_extra=...)``,
            or ``None`` when there is no exdrf metadata to attach.
    """

    name: str
    annotation: str
    title: str
    doc_lines: List[str]
    default_value: str
    description_literal: str
    extra_field_args: str
    json_schema_extra_expr: str | None


@dataclass(frozen=True)
class Db2mRefFieldSpec:
    """One relation field line for an ``Ex`` Pydantic model.

    Attributes:
        name: Relationship attribute name.
        annotation: Full type annotation (e.g. ``PagedList[Tag]`` or
            ``Tag | None``).
        title: Human-readable title for ``Field(title=...)``.
        doc_lines: Description split into lines (for class docstrings only).
        is_list_relation: Whether this is a collection (to-many) side.
        default_value: First positional default for ``Field`` when not a list
            (``...`` or ``None``); unused when ``is_list_relation`` is True.
        description_literal: Python string literal (possibly parenthesized
            implicit concat) for ``Field(description=...)``.
        json_schema_extra_expr: Dict literal or ``None`` when exdrf is empty.
    """

    name: str
    annotation: str
    title: str
    doc_lines: List[str]
    is_list_relation: bool
    default_value: str
    description_literal: str
    json_schema_extra_expr: str | None


@dataclass(frozen=True)
class Al2pdPayloadListFieldSpec:
    """One to-many / M2M payload field (list of ids or composite key dicts).

    Attributes:
        name: Python name (``rel_ids`` or ``rel_keys``).
        annotation: ``list[int]``-like or ``list[dict[str, Any]]``.
        title: Human-readable title for ``Field(title=...)``.
        description_literal: Source for ``Field(description=...)``.
        json_schema_extra_expr: Dict literal or ``None`` when exdrf is empty.
    """

    name: str
    annotation: str
    title: str
    description_literal: str
    json_schema_extra_expr: str | None


def _is_audit_field(name: str) -> bool:
    """Return True if the column name is treated as non-writable audit."""

    return name in _AUDIT_FIELD_NAMES


def resource_generates_edit_payload(model: Any) -> bool:
    """Return whether ``XxxEdit`` is emitted for this resource (al2pd / al2r).

    Composite primary keys with only PK scalars get ``XxxCreate`` only.

    Args:
        model: One ``ExResource`` from the dataset.

    Returns:
        False when al2pd omits ``XxxEdit`` (no PATCH body model).
    """

    # Edit exists unless the table is composite-PK-only (link-style) resource.
    simple_f, extra_f, _refs = partition_fields(model)
    return not _composite_pk_only_link_table(model, simple_f, extra_f)


def _composite_pk_only_link_table(
    model: Any,
    simple_f: List[ExField],
    extra_f: List[ExField],
) -> bool:
    """True when the resource has a composite PK and only PK scalars."""

    # Single-column PKs are never "link-table only" for this rule.
    pnames = set(model.primary_fields())
    if len(pnames) <= 1:
        return False
    scalars = [f for f in simple_f + extra_f]
    if not scalars:
        return False

    # Every non-ref column must be part of the composite primary key.
    for f in scalars:
        if not f.primary:
            return False
    return True


def _scalar_payload_base_ok(field: ExField, excluded_scalar: set[str]) -> bool:
    """Shared filters for Create/Edit scalar payloads."""

    # Drop derived, FK-dependent, audit, and read-only columns from payloads.
    if field.is_derived:
        return False
    if field.name in excluded_scalar:
        return False
    if _is_audit_field(field.name):
        return False
    if getattr(field, "read_only", False):
        return False
    return True


def _collect_create_scalar_fields(
    model: Any,
    simple_f: List[ExField],
    extra_f: List[ExField],
    *,
    excluded_scalar: set[str],
    composite_only: bool,
) -> List[ExField]:
    """Scalars allowed on the Create model."""

    out: List[ExField] = []
    combined = simple_f + extra_f

    # Apply payload filters; composite-only link tables keep PK scalars only.
    for f in combined:
        if not _scalar_payload_base_ok(f, excluded_scalar):
            continue

        # Link-table create body: only primary key columns.
        if composite_only:
            if f.primary:
                out.append(f)
            continue

        # Simple PK tables: omit the lone autoincrement-style PK on create.
        if model.is_primary_simple and f.primary:
            continue
        out.append(f)
    return out


def _collect_edit_scalar_fields(
    model: Any,
    simple_f: List[ExField],
    extra_f: List[ExField],
    *,
    excluded_scalar: set[str],
) -> List[ExField]:
    """Scalars allowed on the Edit model (no primary components)."""

    out: List[ExField] = []
    combined = simple_f + extra_f

    # Same base filters as Create, but never emit primary key columns.
    for f in combined:
        if not _scalar_payload_base_ok(f, excluded_scalar):
            continue
        if f.primary:
            continue
        out.append(f)
    return out


def _collect_list_ref_fields(ref_f: List[ExField]) -> List[ExField]:
    """Reference fields that are collections (payload uses ids/keys)."""

    return [f for f in ref_f if cast(RefBaseField, f).is_list]


def build_payload_list_field_spec(
    field: ExField,
    model_name: str,
) -> Al2pdPayloadListFieldSpec:
    """Build a Create/Edit list payload field for one to-many / M2M relation."""

    rf = cast(RefBaseField, field)
    ref = rf.ref
    pfields = ref.primary_inst_fields()

    # Single PK on the related resource → list of ids; composite → list of
    # dicts.
    if len(pfields) == 1:
        base = scalar_pydantic_type(pfields[0])
        ann = f"list[{base}]"
        suffix = "_ids"
    else:
        ann = "list[dict[str, Any]]"
        suffix = "_keys"

    # Synthesize ``rel_ids`` / ``rel_keys`` plus exdrf metadata for the payload.
    name = f"{rf.name}{suffix}"
    p_ex = _field_exdrf_properties(rf)
    ex_expr = _exdrf_json_schema_extra_expr(p_ex) if p_ex else None
    return Al2pdPayloadListFieldSpec(
        name=name,
        annotation=ann,
        title=rf.title or rf.name.replace("_", " ").title(),
        description_literal=_field_description_literal(rf, extra_field_args=""),
        json_schema_extra_expr=ex_expr,
    )


def scalar_pydantic_type(field: ExField) -> str:
    """Map an exdrf scalar field to a Pydantic type string (without Optional).

    Args:
        field: Non-reference ``ExField`` from the SQLAlchemy dataset.

    Returns:
        A Python type expression as a string.
    """

    # Dispatch on concrete exdrf field classes and a few special type names.
    if isinstance(field, BlobField):
        return "bytes"
    if isinstance(field, BoolField):
        return "bool"
    if isinstance(field, IntListField):
        return "list[int]"
    if isinstance(field, FloatListField):
        return "list[float]"
    if isinstance(field, StrListField):
        return "list[str]"
    if isinstance(field, IntField):
        return "int"
    if isinstance(field, FloatField):
        return "float"
    if isinstance(field, DateField):
        return "date"
    if isinstance(field, DateTimeField):
        return "datetime"
    if isinstance(field, TimeField):
        return "time"
    if field.type_name == FIELD_TYPE_DURATION:
        return "timedelta"
    if isinstance(field, EnumField):
        return "str"
    if isinstance(field, FormattedField):

        # JSON-shaped formatted columns map to ``Any``; other formats stay str.
        if field.format == "json":
            return "Any"
        return "str"
    if isinstance(field, StrField):
        return "str"
    return "str"


def _str_field_constraints(field: ExField) -> str:
    """Build ``Field`` keyword fragment for string-like constraints.

    Args:
        field: Field that may carry min/max length (``StrField`` subclasses).

    Returns:
        Comma-prefixed keyword args, or an empty string.
    """

    # Emit ``min_length`` / ``max_length`` only when the scalar is string-like.
    if not isinstance(field, StrField):
        return ""
    parts: List[str] = []

    # Only emit kwargs that the field actually constrains.
    if field.min_length is not None:
        parts.append(f"min_length={int(field.min_length)}")
    if field.max_length is not None:
        parts.append(f"max_length={int(field.max_length)}")
    if not parts:
        return ""
    return ", " + ", ".join(parts)


def _max_single_line_for_description_literal(extra_field_args: str) -> int:
    """Return max length of a one-line ``json.dumps`` for ``Field``.

    The template appends ``extra_field_args`` and a trailing comma after the
    literal.

    Args:
        extra_field_args: Text after the literal (e.g. ``", max_length=5"``).

    Returns:
        Maximum allowed ``len(json.dumps(...))`` when kept on one source line.
    """

    # Account for ``description=``, trailing ``extra_field_args``, and comma.
    tail = len(extra_field_args) + 1
    return max(
        8,
        _DB2M_MAX_LINE - _FIELD_DESCRIPTION_LINE_PREFIX_LEN - tail,
    )


def _max_json_dumps_slice_end(
    text: str,
    start: int,
    max_encoded_len: int,
) -> int:
    """Largest ``end`` with ``len(json.dumps(text[start:end])) <= max_encoded_len``."""

    n = len(text)
    lo = start + 1
    hi = n
    best = start
    while lo <= hi:
        mid = (lo + hi) // 2
        enc = json.dumps(text[start:mid], ensure_ascii=False)
        if len(enc) <= max_encoded_len:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def _description_slice_end_at_word_boundary(
    text: str,
    start: int,
    end: int,
    max_encoded_len: int,
) -> int:
    """Prefer breaking after the last space before ``end`` when it still fits."""

    n = len(text)
    if end >= n:
        return end
    if end <= start + 1:
        return end
    last_sp = None
    for k in range(end - 1, start - 1, -1):
        if text[k] == " ":
            last_sp = k
            break
    if last_sp is None:
        return end
    candidate = last_sp + 1
    if candidate <= start:
        return end
    lit = json.dumps(text[start:candidate], ensure_ascii=False)
    if len(lit) <= max_encoded_len:
        return candidate
    return end


def _folded_json_string_literal(
    text: str,
    *,
    max_single_line: int,
) -> str:
    """Emit a ``Field`` description literal within ``_DB2M_MAX_LINE``.

    Short strings use a single ``json.dumps`` result. Long strings use
    parenthesized implicit string concatenation over slices of the raw text
    so the decoded value is unchanged. Breaks prefer the last whitespace
    before the width limit so words are not split when possible.

    Args:
        text: Raw description (may contain newlines).
        max_single_line: Maximum length of ``json.dumps(text)`` when emitted
            as a single line (accounts for ``description=`` prefix and tail).

    Returns:
        Source fragment for ``description=`` in generated code.
    """

    # Trivial and short JSON-encoded strings stay on one source line.
    if not text:
        return '""'
    single = json.dumps(text, ensure_ascii=False)
    if len(single) <= max_single_line:
        return single

    # Inside ``Field(``, continuation lines use 12 spaces so closers align
    # with the ``description=(`` line (8 spaces + 4 for nesting).
    inner_indent = "            "
    max_lit = max(8, _DB2M_MAX_LINE - len(inner_indent))
    parts: List[str] = []
    i = 0
    n = len(text)

    # Binary search each segment for max length under ``max_lit``, then snap to
    # a trailing space when one exists before that end.
    while i < n:
        j = _max_json_dumps_slice_end(text, i, max_lit)
        if j <= i:
            parts.append(json.dumps(text[i : i + 1], ensure_ascii=False))
            i += 1
            continue
        j = _description_slice_end_at_word_boundary(text, i, j, max_lit)
        parts.append(json.dumps(text[i:j], ensure_ascii=False))
        i = j

    # Parenthesized implicit concat across lines inside ``Field(...)``.
    if len(parts) == 1:
        return parts[0]
    inner = inner_indent + (f"\n{inner_indent}").join(parts)
    close_paren = "        )"
    return f"(\n{inner}\n{close_paren}"


def _field_description_literal(
    field: ExField,
    *,
    extra_field_args: str = "",
) -> str:
    """Return a Python string literal for Pydantic ``Field(description=)``.

    Args:
        field: exdrf field with ``description`` and ``doc_lines``.
        extra_field_args: Characters between the literal and the line-ending
            comma in the template (e.g. string constraints).

    Returns:
        A string that is safe to embed as ``description=<return>`` in code.
    """

    # Prefer ``description``; fall back to joined doc lines; fold to line width.
    raw = (field.description or "").strip()
    if not raw:
        raw = "\n".join(field.doc_lines)
    budget = _max_single_line_for_description_literal(extra_field_args)
    return _folded_json_string_literal(raw, max_single_line=budget)


def _field_exdrf_properties(field: ExField) -> dict:
    """Field exdrf dict from :meth:`~exdrf.field.ExField.field_properties`."""

    # Prose stays on ``description`` only (no duplicate ``doc`` line list).
    props = dict(field.field_properties(explicit=False))
    _strip_al2pd_exdrf_redundant(props)

    # ``field_properties`` emits ``read_only`` only when false; we want the
    # key present solely for true (read-only columns).
    props.pop("read_only", None)
    if getattr(field, "read_only", False):
        props["read_only"] = True

    # Default UI bucket is ``general``; omit it, keep non-default categories.
    if props.get("category") == "general":
        props.pop("category", None)
    return props


def build_scalar_field_spec(
    field: ExField,
    _model_name: str,
) -> Db2mScalarFieldSpec:
    """Create a :class:`Db2mScalarFieldSpec` for one scalar column.

    Args:
        field: Non-reference field.
        _model_name: PascalCase resource name (kept for call-site stability).

    Returns:
        Specification for template rendering.
    """

    # Annotation, defaults, string ``Field`` kwargs, exdrf json_schema_extra.
    base = scalar_pydantic_type(field)
    ann = optionalize(base, field.nullable)

    # Required columns use ``...``; nullable columns default to ``None``.
    if field.nullable:
        default_value = "None"
    else:
        default_value = "..."
    extra = _str_field_constraints(field)
    p_ex = _field_exdrf_properties(field)
    ex_expr = _exdrf_json_schema_extra_expr(p_ex) if p_ex else None

    # Frozen record consumed by ``interface.py.j2`` for one column.
    return Db2mScalarFieldSpec(
        name=field.name,
        annotation=ann,
        title=field.title or field.name.replace("_", " ").title(),
        doc_lines=list(field.doc_lines),
        default_value=default_value,
        description_literal=_field_description_literal(
            field,
            extra_field_args=extra,
        ),
        extra_field_args=extra,
        json_schema_extra_expr=ex_expr,
    )


def build_ref_field_spec(
    field: ExField,
    _model_name: str,
) -> Db2mRefFieldSpec:
    """Create a :class:`Db2mRefFieldSpec` for one ORM relationship field.

    Args:
        field: Reference field (``RefBaseField`` subclass).
        _model_name: PascalCase resource name (kept for call-site stability).

    Returns:
        Specification for template rendering.
    """

    # Lists use ``PagedList[Target]``; singles use optional related model type.
    rf = cast(RefBaseField, field)
    ref_name = rf.ref.name
    if rf.is_list:
        ann = f"PagedList[{ref_name}]"
        default_value = ""
    else:
        ann = optionalize(ref_name, rf.nullable)
        default_value = "None" if rf.nullable else "..."

    # Relation fields share the same exdrf json_schema_extra pattern as scalars.
    p_ex = _field_exdrf_properties(field)
    ex_expr = _exdrf_json_schema_extra_expr(p_ex) if p_ex else None

    # Frozen record for one relationship line on the ``Ex`` model.
    return Db2mRefFieldSpec(
        name=field.name,
        annotation=ann,
        title=field.title or field.name.replace("_", " ").title(),
        doc_lines=list(field.doc_lines),
        is_list_relation=bool(rf.is_list),
        default_value=default_value,
        description_literal=_field_description_literal(
            field,
            extra_field_args="",
        ),
        json_schema_extra_expr=ex_expr,
    )


def ex_type_checking_deps(ref_fields: List[ExField]) -> List:
    """Collect related resources referenced by relation fields (unique, sorted).

    Args:
        ref_fields: ORM reference fields from :func:`partition_fields`.

    Returns:
        List of ``ExResource`` / ``Resource`` instances.
    """

    # Dedupe TYPE_CHECKING targets by related resource name (stable order).
    by_name = {}
    for fld in ref_fields:
        rf = cast(RefBaseField, fld)
        if rf.ref is not None:
            by_name[rf.ref.name] = rf.ref
    return sorted(by_name.values(), key=lambda r: r.name)


def collect_typing_imports(
    scalar_fields: List[ExField],
) -> Tuple[bool, bool, bool, bool, bool]:
    """Decide which ``datetime`` / ``typing`` symbols the module needs.

    Args:
        scalar_fields: Original scalar ``ExField`` instances (simple + Ex-only).

    Returns:
        Tuple ``(need_date, need_datetime, need_time, need_timedelta,
        need_any)``.
    """

    # Scan scalar field types for symbols that need ``datetime`` or ``typing``.
    need_date = any(isinstance(f, DateField) for f in scalar_fields)
    need_datetime = any(isinstance(f, DateTimeField) for f in scalar_fields)
    need_time = any(isinstance(f, TimeField) for f in scalar_fields)
    need_td = any(f.type_name == FIELD_TYPE_DURATION for f in scalar_fields)
    need_any = any(
        isinstance(f, FormattedField) and f.format == "json"
        for f in scalar_fields
    )
    return (need_date, need_datetime, need_time, need_td, need_any)


def db2m_rel_path_to_import_prefix(dep_path: str) -> str:
    """Map :meth:`~exdrf.resource.ExResource.rel_import` paths to import dots.

    ``rel_import`` joins segments with ``/`` (for example ``../files``). A naive
    ``replace('/', '.')`` turns ``../files`` into ``...files`` (three dots),
    which is the wrong relative-import depth. This helper maps slash paths to
    the prefix placed before ``.<module_stem>`` in ``from ... import``.

    Args:
        dep_path: Non-empty slash-separated relative path, or ``""`` for a
            same-package import.

    Returns:
        Dotted prefix such as ``..files`` or ``...ancpi``, or ``""`` when
        ``dep_path`` is empty.
    """

    # Empty path → same-package import; else split ``..`` vs named segments.
    if not dep_path:
        return ""
    parts = [p for p in dep_path.split("/") if p]
    up = 0
    rest: List[str] = []
    for piece in parts:
        if piece == "..":
            up += 1
        else:
            rest.append(piece)

    # One dot per ``..`` plus one for the relative-import root segment.
    prefix = "." * (up + 1)
    tail = ".".join(rest)
    if tail:
        return f"{prefix}{tail}"
    return prefix


def build_al2pd_template_kwargs(model: Any) -> dict:
    """Assemble kwargs for ``al2pd/interface.py.j2`` and dependency imports.

    Args:
        model: One resource from an ``ExDataset`` (SQLAlchemy-backed).

    Returns:
        Dict suitable for ``write_resource_template_file(..., **kwargs)``.
    """

    # Partition ORM columns (simple / Ex-only / refs); build line specs.
    simple_f, extra_f, ref_f = partition_fields(model)
    mname = model.name
    model_snake = re.sub(r"(?<!^)(?=[A-Z])", "_", mname).lower()
    simple_specs = [build_scalar_field_spec(f, mname) for f in simple_f]
    extra_specs = [build_scalar_field_spec(f, mname) for f in extra_f]
    ref_specs = [build_ref_field_spec(f, mname) for f in ref_f]

    # Depends-on FK scalars and composite link tables drive Create/Edit.
    excluded_scalar = depends_on_fk_field_names(model)
    composite_only = _composite_pk_only_link_table(model, simple_f, extra_f)
    generate_edit = not composite_only

    # Create/Edit scalars and list-shaped relation payloads for templates.
    create_scalar_fields = _collect_create_scalar_fields(
        model,
        simple_f,
        extra_f,
        excluded_scalar=excluded_scalar,
        composite_only=composite_only,
    )

    # No Edit model for composite-PK-only resources; skip edit field lists.
    edit_scalar_fields = (
        _collect_edit_scalar_fields(
            model,
            simple_f,
            extra_f,
            excluded_scalar=excluded_scalar,
        )
        if generate_edit
        else []
    )
    list_ref_fields = _collect_list_ref_fields(ref_f)
    payload_list_specs = [
        build_payload_list_field_spec(f, mname) for f in list_ref_fields
    ]

    # Field specs for the Create/Edit models (subset of columns).
    create_scalar_specs = [
        build_scalar_field_spec(f, mname) for f in create_scalar_fields
    ]
    edit_scalar_specs = [
        build_scalar_field_spec(f, mname) for f in edit_scalar_fields
    ]

    # ``datetime`` imports and ``Any`` for JSON / composite list payloads.
    need_date, need_dt, need_time, need_td, need_any = collect_typing_imports(
        simple_f + extra_f
    )
    need_any_payload = need_any or any(
        "dict[str, Any]" in s.annotation for s in payload_list_specs
    )

    # TYPE_CHECKING import targets and dotted relative prefixes for ``from``.
    # Drop the emitting model from relation deps: a TYPE_CHECKING import from
    # the same module redefines the class symbol and triggers flake8 F811.
    deps = [d for d in ex_type_checking_deps(ref_f) if d.name != mname]
    dep_paths = [model.rel_import(d) for d in deps]
    dep_import_prefixes = [db2m_rel_path_to_import_prefix(p) for p in dep_paths]

    # Build the comma-separated datetime symbol list for the import line.
    dt_names: List[str] = []
    if need_date:
        dt_names.append("date")
    if need_dt:
        dt_names.append("datetime")
    if need_time:
        dt_names.append("time")
    if need_td:
        dt_names.append("timedelta")

    # Google-style doc bodies for base, Ex, Create, and optional Edit classes.
    summary = model_summary_one_line(model)
    doc_body = build_google_db2m_class_doc_body(
        summary,
        simple_f,
        f"{model.name} (generated).",
    )

    # ``Ex`` doc lists every column and relationship on the read model.
    ex_doc_fields: List[ExField] = list(simple_f) + list(extra_f) + list(ref_f)
    doc_ex_body = build_google_db2m_class_doc_body(
        summary,
        ex_doc_fields,
        f"{model.name}Ex (generated).",
    )

    # Create/Edit docs mention only writable payload fields (scalars + lists).
    doc_create_body = build_google_db2m_class_doc_body(
        summary,
        create_scalar_fields + list_ref_fields,
        f"{model.name}Create (generated).",
    )

    doc_edit_body = (
        build_google_db2m_class_doc_body(
            summary,
            edit_scalar_fields + list_ref_fields,
            f"{model.name}Edit (generated).",
        )
        if generate_edit
        else ""
    )

    # Module-level dict literal for resource exdrf only when non-empty.
    res_props = dict(model.resource_properties(explicit=False))
    _strip_al2pd_exdrf_redundant(res_props)

    exdrf_assignments: List[Tuple[str, str]] = []
    res_var: str | None = None
    if res_props:
        res_var = _exdrf_resource_var(mname)
        res_rhs = _exdrf_dict_rhs(res_props, assignee=res_var)
        exdrf_assignments.append((res_var, res_rhs))

    # Template flag: import ``PagedList`` when any relation is a collection.
    need_paged = any(s.is_list_relation for s in ref_specs)

    # Single dict passed into ``interface.py.j2`` and sibling generators.
    return {
        "al2pd_simple_fields": simple_specs,
        "al2pd_ex_scalar_fields": extra_specs,
        "al2pd_ex_ref_fields": ref_specs,
        "al2pd_class_doc_body": doc_body,
        "al2pd_ex_class_doc_body": doc_ex_body,
        "al2pd_create_class_doc_body": doc_create_body,
        "al2pd_edit_class_doc_body": doc_edit_body,
        "al2pd_create_scalar_fields": create_scalar_specs,
        "al2pd_edit_scalar_fields": edit_scalar_specs,
        "al2pd_payload_list_fields": payload_list_specs,
        "al2pd_generate_edit": generate_edit,
        "al2pd_datetime_imports": ", ".join(dt_names),
        "al2pd_import_any": need_any_payload,
        "deps": deps,
        "dep_paths": dep_paths,
        "al2pd_exdrf_assignments": exdrf_assignments,
        "al2pd_resource_exdrf_var": res_var,
        "al2pd_need_paged_list": need_paged,
        "al2pd_model_snake": model_snake,
        "al2pd_dep_import_prefixes": dep_import_prefixes,
    }
