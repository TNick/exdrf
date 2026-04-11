"""List-relation GET route metadata for generated ``resource_router.py.j2``.

This module stays free of ``exdrf`` imports so lightweight tests can load it
via ``importlib`` without installing the full exdrf stack.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


def parse_paged_list_inner_type(annotation: str) -> str | None:
    """Return the item type name inside ``PagedList[...]`` if it matches.

    Args:
        annotation: String such as ``PagedList[Tag]`` from al2pd ref specs.

    Returns:
        The inner symbol (e.g. ``Tag``), or ``None`` if not a simple match.
    """

    text = (annotation or "").strip()
    m = re.fullmatch(r"PagedList\[(\w+)\]", text)
    if m is None:
        return None
    return m.group(1)


def build_al2r_list_relation_route_specs(
    pd_kw: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Build per-relation GET list route metadata for ``resource_router.py.j2``.

    Args:
        pd_kw: Template kwargs from
            :func:`~exdrf_gen_al2pd.pydantic_emit.build_al2pd_template_kwargs`.

    Returns:
        One dict per list relation with keys ``attr`` (ORM / field name) and
        ``related_name`` (inner Pydantic base class name, not ``*Ex``).
    """

    out: List[Dict[str, str]] = []
    for field in pd_kw.get("al2pd_ex_ref_fields") or ():
        if not getattr(field, "is_list_relation", False):
            continue
        related = parse_paged_list_inner_type(getattr(field, "annotation", ""))
        if not related:
            continue
        name = getattr(field, "name", "") or ""
        if not name:
            continue
        out.append({"attr": name, "related_name": related})
    return out
