"""Build ``al2r_relation_sync_specs`` for generated FastAPI route modules."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple, cast

from exdrf.field_types.ref_base import RefBaseField
from exdrf.field_types.ref_m2m import RefManyToManyField
from exdrf.field_types.ref_o2m import RefOneToManyField
from exdrf_gen_al2pd.field_partition import partition_fields
from exdrf_gen_al2pd.pydantic_emit import build_payload_list_field_spec


def _same_resource(a: Any, b: Any) -> bool:
    """Return True when ``a`` and ``b`` name the same logical resource."""

    return a.name == b.name and tuple(
        getattr(a, "categories", ()) or ()
    ) == tuple(
        getattr(b, "categories", ()) or (),
    )


def _junction_parent_and_related_fks(
    inter: Any,
    parent: Any,
    related: Any,
) -> Tuple[List[str], List[str]]:
    """Split junction scalar FK columns into parent-side vs related-side lists.

    Args:
        inter: Intermediate ``ExResource`` (junction table).
        parent: Owner resource.
        related: Related resource on the other side of the M2M / bridge.

    Returns:
        Two lists of column names on ``inter`` (parent FKs first in declaration
        order, then related FKs). Either list may be empty when inference fails.
    """

    parent_cols: List[str] = []
    related_cols: List[str] = []
    for f in inter.fields:
        if getattr(f, "is_ref_type", False):
            continue
        fk_to = getattr(f, "fk_to", None)
        if fk_to is None:
            continue
        ref = getattr(fk_to, "ref", None)
        if ref is None:
            continue
        if _same_resource(ref, parent):
            parent_cols.append(f.name)
        elif _same_resource(ref, related):
            related_cols.append(f.name)
    return parent_cols, related_cols


def _m2m_secondary_fk_column_names_from_sa(
    rel_prop: Any,
    parent_table: Any,
) -> Tuple[List[str], List[str]]:
    """Infer junction column names from a SQLAlchemy M2M relationship.

    Used when intermediate ``ExResource`` fields lack ``fk_to`` metadata
    (common on pure association tables).

    Args:
        rel_prop: ``RelationshipProperty`` from the parent resource.
        parent_table: SQLAlchemy ``Table`` for the parent mapped class.

    Returns:
        ``(parent_side_cols, related_side_cols)`` on the secondary table.
    """

    secondary = getattr(rel_prop, "secondary", None)
    if secondary is None:
        return [], []
    parent_cols: List[str] = []
    related_cols: List[str] = []
    pairs = getattr(rel_prop, "local_remote_pairs", None) or ()
    for left, right in pairs:
        if left.table is secondary and right.table is not secondary:
            sec_col, other = left, right
        elif right.table is secondary and left.table is not secondary:
            sec_col, other = right, left
        else:
            continue
        if other.table is parent_table:
            parent_cols.append(sec_col.key)
        else:
            related_cols.append(sec_col.key)
    return parent_cols, related_cols


def _o2m_child_fk_column_from_sa(rfb: Any, parent_res: Any) -> str | None:
    """Return the child-table FK column for a OneToMany ``RelationshipProperty``.

    When the child has several FKs to the same parent (e.g. ``Town`` with
    ``entity_id``, ``mayor_id``, …), exdrf scalar ``fk_to`` metadata is
    ambiguous; SQLAlchemy ``synchronize_pairs`` identifies the correct column.

    Args:
        rfb: ``RefOneToManyField`` (or compatible) with ``src`` set to the
            SQLAlchemy relationship.
        parent_res: ``ExResource`` for the parent model.

    Returns:
        Child column name, or ``None`` when inference is not possible.
    """

    rel = getattr(rfb, "src", None)
    pairs = getattr(rel, "synchronize_pairs", None)
    if not pairs or len(pairs) != 1:
        return None
    left, right = pairs[0]
    pt = getattr(getattr(parent_res, "src", None), "__table__", None)
    if pt is None:
        return None
    if left.table is pt:
        return right.key
    if right.table is pt:
        return left.key
    return None


def _child_fk_toward_parent(child: Any, parent: Any) -> str | None:
    """Find the scalar FK column on ``child`` that references ``parent``."""

    for f in child.fields:
        if getattr(f, "is_ref_type", False):
            continue
        fk_to = getattr(f, "fk_to", None)
        if fk_to is None:
            continue
        ref = getattr(fk_to, "ref", None)
        if ref is not None and _same_resource(ref, parent):
            return f.name
    return None


def _single_child_pk_name(child: Any) -> str | None:
    """Return the sole primary-key column name when it is a simple PK."""

    names = list(child.primary_fields())
    if len(names) == 1:
        return names[0]
    return None


def _related_orm_class_name(related: Any) -> str:
    """Return the SQLAlchemy mapped class name for a related ``ExResource``."""

    src = getattr(related, "src", None)
    if src is None:
        return ""
    return getattr(src, "__name__", "") or ""


def build_al2r_relation_sync_specs(
    model: Any,
) -> Tuple[List[Dict[str, Any]], bool]:
    """Derive relation list persistence metadata for ``resource_router.py.j2``.

    Args:
        model: One ``ExResource`` from an SQLAlchemy-backed dataset.

    Returns:
        A pair ``(specs, all_supported)``. When ``all_supported`` is False, the
        generator should keep the legacy ``NotImplementedError`` guard for list
        payloads on this resource.
    """

    _, _, ref_f = partition_fields(model)
    list_refs = [f for f in ref_f if cast(RefBaseField, f).is_list]
    if not list_refs:
        return [], True

    specs: List[Dict[str, Any]] = []
    all_supported = True
    parent_pk = tuple(model.primary_fields())

    for rf in list_refs:
        rfb = cast(RefBaseField, rf)
        pls = build_payload_list_field_spec(rfb, model.name)
        payload_name = pls.name
        related_simple = len(rfb.ref.primary_inst_fields()) == 1

        if isinstance(rfb, RefManyToManyField):
            inter = rfb.ref_intermediate
            related = rfb.ref
            pcols, rcols = _junction_parent_and_related_fks(
                inter,
                model,
                related,
            )
            if len(pcols) != len(parent_pk) or not rcols:
                rel_src = getattr(rfb, "src", None)
                parent_tbl = getattr(
                    getattr(model, "src", None),
                    "__table__",
                    None,
                )
                if (
                    rel_src is not None
                    and parent_tbl is not None
                    and getattr(rel_src, "secondary", None) is not None
                ):
                    p2, r2 = _m2m_secondary_fk_column_names_from_sa(
                        rel_src,
                        parent_tbl,
                    )
                    if len(p2) == len(parent_pk) and r2:
                        pcols, rcols = p2, r2
            if len(pcols) != len(parent_pk) or not rcols:
                all_supported = False
                continue
            if related_simple:
                if len(rcols) != 1:
                    all_supported = False
                    continue
                related_fk = rcols[0]
            else:
                if len(rcols) != len(rfb.ref.primary_inst_fields()):
                    all_supported = False
                    continue
                related_fk = ""
            assoc_name = inter.src.__name__ if inter.src is not None else ""
            if not assoc_name:
                all_supported = False
                continue
            specs.append(
                {
                    "kind": "m2m",
                    "ex_field_name": rf.name,
                    "payload_name": payload_name,
                    "assoc_class": assoc_name,
                    "parent_fk_cols": tuple(pcols),
                    "related_fk_col": related_fk,
                    "parent_pk_attrs": parent_pk,
                    "related_pk_simple": related_simple,
                    "related_orm_class": _related_orm_class_name(related),
                },
            )
            continue

        if isinstance(rfb, RefOneToManyField):
            child = rfb.ref
            bridge_name = getattr(rfb, "bridge", None)
            if bridge_name:
                try:
                    inter = model.dataset[bridge_name]
                except KeyError:
                    all_supported = False
                    continue
                related = child
                pcols, rcols = _junction_parent_and_related_fks(
                    inter,
                    model,
                    related,
                )
                if len(pcols) != len(parent_pk) or not rcols:
                    rel_src = getattr(rfb, "src", None)
                    parent_tbl = getattr(
                        getattr(model, "src", None),
                        "__table__",
                        None,
                    )
                    if (
                        rel_src is not None
                        and parent_tbl is not None
                        and getattr(rel_src, "secondary", None) is not None
                    ):
                        p2, r2 = _m2m_secondary_fk_column_names_from_sa(
                            rel_src,
                            parent_tbl,
                        )
                        if len(p2) == len(parent_pk) and r2:
                            pcols, rcols = p2, r2
                if len(pcols) != len(parent_pk) or not rcols:
                    all_supported = False
                    continue
                if related_simple:
                    if len(rcols) != 1:
                        all_supported = False
                        continue
                    related_fk = rcols[0]
                else:
                    if len(rcols) != len(rfb.ref.primary_inst_fields()):
                        all_supported = False
                        continue
                    related_fk = ""
                assoc_name = inter.src.__name__ if inter.src is not None else ""
                if not assoc_name:
                    all_supported = False
                    continue
                specs.append(
                    {
                        "kind": "o2m_bridge",
                        "ex_field_name": rf.name,
                        "payload_name": payload_name,
                        "assoc_class": assoc_name,
                        "parent_fk_cols": tuple(pcols),
                        "related_fk_col": related_fk,
                        "parent_pk_attrs": parent_pk,
                        "related_pk_simple": related_simple,
                        "related_orm_class": _related_orm_class_name(related),
                    },
                )
                continue

            fk = _o2m_child_fk_column_from_sa(
                rfb, model
            ) or _child_fk_toward_parent(
                child,
                model,
            )
            if fk is None or len(parent_pk) != 1:
                all_supported = False
                continue
            cname = child.src.__name__ if child.src is not None else ""
            if not cname:
                all_supported = False
                continue
            pkc = _single_child_pk_name(child)
            if pkc is not None:
                specs.append(
                    {
                        "kind": "o2m_fk",
                        "ex_field_name": rf.name,
                        "payload_name": payload_name,
                        "child_class": cname,
                        "child_fk_col": fk,
                        "child_pk_col": pkc,
                        "parent_pk_attrs": parent_pk,
                    },
                )
            else:
                specs.append(
                    {
                        "kind": "o2m_child_rows",
                        "ex_field_name": rf.name,
                        "payload_name": payload_name,
                        "assoc_class": cname,
                        "parent_fk_cols": (fk,),
                        "related_fk_col": "",
                        "parent_pk_attrs": parent_pk,
                        "related_pk_simple": related_simple,
                    },
                )
            continue

        all_supported = False

    if len(specs) != len(list_refs):
        all_supported = False

    return specs, all_supported


def extra_orm_classes_for_relations(
    orm_class_name: str,
    specs: List[Dict[str, Any]],
) -> List[str]:
    """ORM class names to import from ``db_module`` beyond the main resource."""

    out: List[str] = []
    seen = {orm_class_name}
    for sp in specs:
        cls = sp.get("assoc_class") or sp.get("child_class")
        if cls and cls not in seen:
            seen.add(cls)
            out.append(cls)
        rel_cls = sp.get("related_orm_class") or ""
        if rel_cls and rel_cls not in seen:
            seen.add(rel_cls)
            out.append(rel_cls)
    return sorted(out)


def _al2r_schema_import_symbol_names(
    resource_name: str,
    list_rel_types: List[str],
    generate_edit: bool,
) -> frozenset[str]:
    """Return names imported from the Pydantic schema module for a resource."""

    names = {f"{resource_name}Create", f"{resource_name}Ex", *list_rel_types}
    if generate_edit:
        names.add(f"{resource_name}Edit")
    return frozenset(names)


def _al2r_orm_db_import_names(
    orm_class_name: str,
    extra_orms: List[str],
) -> frozenset[str]:
    """Return ORM class names imported from ``db_module``."""

    return frozenset({orm_class_name, *extra_orms})


def al2r_orm_schema_name_collisions(
    orm_class_name: str,
    extra_orms: List[str],
    resource_name: str,
    list_rel_types: List[str],
    generate_edit: bool,
) -> frozenset[str]:
    """Names that would be imported twice from ORM and schema (Flake8 F811).

    Such symbols are emitted as ``NameOrm`` on the ORM import side.

    Args:
        orm_class_name: Primary mapped class name for the resource.
        extra_orms: Additional ORM classes from relation sync specs.
        resource_name: ``ExResource.name`` (Pydantic ``*Create`` / ``*Ex`` stem).
        list_rel_types: Related read-model names from list-relation routes.
        generate_edit: Whether ``*Edit`` is imported from the schema module.

    Returns:
        Intersection of ORM import names and schema import names.
    """

    return _al2r_orm_db_import_names(
        orm_class_name,
        extra_orms,
    ) & _al2r_schema_import_symbol_names(
        resource_name,
        list_rel_types,
        generate_edit,
    )
