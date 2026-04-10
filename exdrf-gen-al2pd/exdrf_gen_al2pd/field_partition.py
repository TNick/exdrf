"""Partition exdrf-like resources for al2pd without importing application code."""

from __future__ import annotations

from typing import Any, List, Set, Tuple


def depends_on_fk_field_names(model: Any) -> Set[str]:
    """Field names supplied by API/session context, not request bodies.

    Uses ``Resource.depends_on``: each ``(concept, field_name)`` pair names a
    column (e.g. ``org_id``) that should be omitted from generated Pydantic
    input models, along with the ORM relation backed by that FK (e.g.
    ``org``).

    Args:
        model: Resource with optional ``depends_on`` list of pairs.

    Returns:
        Set of scalar field names to exclude from simple and Ex scalars.
    """

    # ``depends_on`` entries are (concept, field_name) pairs; keep FK column
    # names only.
    raw = getattr(model, "depends_on", None) or ()
    out: Set[str] = set()
    for item in raw:

        # Ignore malformed entries; second element must be a non-empty str.
        if isinstance(item, (tuple, list)) and len(item) >= 2:
            name = item[1]
            if isinstance(name, str) and name.strip():
                out.add(name.strip())
    return out


def format_db2m_class_doc_body(
    doc_lines: List[str],
    fallback_summary: str,
) -> str:
    """Format resource doc lines for a class docstring body.

    Non-empty lines are indented with four spaces. Empty lines stay blank
    (no trailing spaces). Leading and trailing blank lines are removed.

    Args:
        doc_lines: Lines from ``Resource.doc_lines``.
        fallback_summary: Single-line text when there are no doc lines.

    Returns:
        Text between the opening and closing docstring quotes in generated
        modules (each non-blank line starts with four spaces).
    """

    lines = list(doc_lines)

    # Strip leading and trailing blank lines from the logical doc block.
    while lines and not (lines[0] or "").strip():
        lines.pop(0)
    while lines and not (lines[-1] or "").strip():
        lines.pop()

    # No content after trim: emit a single indented summary line.
    if not lines:
        return f"    {fallback_summary}"
    body: List[str] = []

    # Non-empty lines get one four-space indent; blank lines collapse doubles.
    for line in lines:
        if (line or "").strip():
            body.append(f"    {line}")
        else:
            if body and body[-1] == "":
                continue
            body.append("")

    # Drop a trailing blank line before joining into the docstring body.
    while body and body[-1] == "":
        body.pop()
    return "\n".join(body)


def optionalize(annotation: str, nullable: bool) -> str:
    """Append ``| None`` when the column allows NULL.

    Args:
        annotation: Base type as a string.
        nullable: Whether the underlying field is nullable.

    Returns:
        The annotation string, optionally unioned with ``None``.
    """

    # Nullable ORM columns become ``T | None`` in generated Pydantic types.
    if nullable:
        return f"{annotation} | None"
    return annotation


def partition_fields(model: Any) -> Tuple[List[Any], List[Any], List[Any]]:
    """Split fields into simple scalars, extra scalars for Ex, and relations.

    Simple scalars: only names in ``minimum_field_set`` (label + primary
    keys), excluding ``is_derived`` search-only fields and scalars listed in
    ``depends_on`` (e.g. ``org_id`` for tenant context).

    Ex-only scalars: remaining non-reference, non-derived scalars, except
    ``depends_on`` targets.

    Relations: reference fields except those tied to an excluded FK via
    ``fk_from`` (e.g. drop ``org`` when ``org_id`` is context-only).

    Args:
        model: Resource with ``sorted_fields``, ``minimum_field_set``, and
            optional ``depends_on``.

    Returns:
        ``(simple_scalars, ex_only_scalars, ref_fields)`` in ``sorted_fields``
        order.
    """

    # Label + PK columns define the slim read surface; ``depends_on`` drops
    # context FK scalars (and their relations) from payloads.
    minimum: Set[str] = set(model.minimum_field_set)
    excluded_scalar: Set[str] = depends_on_fk_field_names(model)
    simple: List[Any] = []
    simple_names: Set[str] = set()

    # First pass: non-ref, non-derived scalars in ``minimum_field_set``.
    for fld in model.sorted_fields:
        if fld.is_ref_type or fld.is_derived:
            continue
        if fld.name in excluded_scalar:
            continue
        if fld.name in minimum:
            simple.append(fld)
            simple_names.add(fld.name)

    # Second pass: other eligible scalars become Ex-only (not in ``simple``).
    extra: List[Any] = []
    for fld in model.sorted_fields:
        if fld.is_ref_type or fld.is_derived:
            continue
        if fld.name in excluded_scalar:
            continue
        if fld.name not in simple_names:
            extra.append(fld)

    # Third pass: relations, but skip ones whose backing FK is context-only.
    refs: List[Any] = []
    for fld in model.sorted_fields:
        if not fld.is_ref_type:
            continue
        fk_from = getattr(fld, "fk_from", None)
        if fk_from is not None and fk_from.name in excluded_scalar:
            continue
        refs.append(fld)

    # Order matches ``model.sorted_fields`` because each pass walks it in order.
    return simple, extra, refs
