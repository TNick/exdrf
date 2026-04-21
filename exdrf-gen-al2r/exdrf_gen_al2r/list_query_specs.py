"""Merge list-route metadata with relation sync specs for AL2R queries."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple, cast


def build_al2r_list_relation_query_specs(
    resource: Any,
    list_rel_specs: List[Dict[str, str]],
    rel_specs: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Attach ``sync`` and ``related_pk_col`` to each list-relation route spec.

    Args:
        resource: ``ExResource`` whose ``fields`` resolve list refs.
        list_rel_specs: Output of
            :func:`~exdrf_gen_al2r.list_route_specs.build_al2r_list_relation_route_specs`.
        rel_specs: Output of
            :func:`~exdrf_gen_al2r.relation_specs.build_al2r_relation_sync_specs`.

    Returns:
        One dict per list route with original keys plus ``sync`` (the matching
        relation spec dict or ``None``), ``related_pk_col`` (single ORM PK
        column for ``m2m`` joins; default ``id``), and optional
        ``related_pk_order`` (all PK columns for ``ORDER BY`` when the related
        resource has a composite primary key).
    """

    by_ex: Dict[str, Dict[str, Any]] = {
        cast(str, s["ex_field_name"]): s
        for s in rel_specs
        if s.get("ex_field_name")
    }
    ref_by_name: Dict[str, Any] = {}
    for f in getattr(resource, "fields", ()) or ():
        if getattr(f, "is_list", False) and getattr(f, "name", None):
            ref_by_name[cast(str, f.name)] = f

    out: List[Dict[str, Any]] = []
    for lr in list_rel_specs:
        attr = lr.get("attr") or ""
        sync = by_ex.get(attr)
        rf = ref_by_name.get(attr)
        rel_pk = "id"
        rel_pk_order: Tuple[str, ...] | None = None
        if rf is not None:
            ref = getattr(rf, "ref", None)
            if ref is not None:
                pnames = tuple(ref.primary_fields())
                if len(pnames) == 1:
                    rel_pk = pnames[0]
                elif len(pnames) > 1:
                    rel_pk = pnames[0]
                    rel_pk_order = pnames
        row = {
            **lr,
            "sync": sync,
            "related_pk_col": rel_pk,
            "related_pk_order": rel_pk_order,
        }
        out.append(row)
    return out
