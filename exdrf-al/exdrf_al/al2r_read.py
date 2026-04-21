"""SQLAlchemy-backed reads for AL2R list APIs.

Builds filtered, sorted, paged queries for root resources and for nested
relation lists (one-to-many FK, many-to-many, bridge, and child-row shapes).
Results are mapped to Pydantic ``Ex`` / related DTOs and wrapped in
:class:`exdrf_pd.paged.PagedList`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Sequence, TypeVar

from exdrf.sa_filter_op import filter_op_registry
from exdrf_pd.filter_item import FilterItem
from exdrf_pd.paged import PagedList
from exdrf_pd.sort_item import SortItem
from pydantic import BaseModel
from sqlalchemy import Select, and_, func, select
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

TEx = TypeVar("TEx", bound=BaseModel)


@dataclass(frozen=True)
class RelationListSpec:
    """Static description of how to load one nested list on an ``*Ex`` row.

    ``kind`` matches the relation shapes emitted by ``exdrf-gen-al2r`` sync
    metadata. Callers pair each spec with the parent ORM row and optional
    filter/sort JSON to produce a :class:`PagedList` of ``related_schema``
    instances.

    Attributes:
        kind: Relation shape: ``o2m_fk``, ``m2m``, ``o2m_bridge``, or
            ``o2m_child_rows``.
        parent_pk_attrs: Names of parent PK columns on the owning ORM row.
        related_model: SQLAlchemy mapped class for related table rows.
        related_schema: Pydantic model (base related type, not ``*Ex``) for
            each item in the nested list.
        related_pk_col: Single ORM column used for ``m2m`` / ``o2m_bridge``
            join keys (the junction FK targets this column on ``related_model``).
        related_pk_order: ORM column names for default ``ORDER BY`` and
            tie-breakers; use every PK column when the related table has a
            composite key. When ``None``, callers use ``(related_pk_col,)``.
        child_fk_col: On ``o2m_fk`` / ``o2m_child_rows``, FK column on
            ``related_model`` pointing at the parent.
        assoc_model: Junction ORM class for ``m2m`` and ``o2m_bridge``.
        parent_fk_cols: Junction column names that reference the parent PK.
        related_fk_col: Junction column that references ``related_pk_col`` on
            ``related_model`` (``m2m`` / ``o2m_bridge`` only).
    """

    kind: str
    parent_pk_attrs: tuple[str, ...]
    related_model: type[Any]
    related_schema: type[BaseModel]
    related_pk_col: str
    related_pk_order: tuple[str, ...] | None = None
    child_fk_col: str | None = None
    assoc_model: type[Any] | None = None
    parent_fk_cols: tuple[str, ...] | None = None
    related_fk_col: str | None = None


def relation_list_spec_from_sync(
    sync: dict[str, Any],
    *,
    related_model: type[Any],
    related_schema: type[BaseModel],
    related_pk_col: str,
    related_pk_order: tuple[str, ...] | None = None,
) -> RelationListSpec:
    """Build a :class:`RelationListSpec` from string-only sync dict plus ORM.

    Args:
        sync: Relation metadata from
            :func:`~exdrf_gen_al2r.relation_specs.build_al2r_relation_sync_specs`
            (no ORM classes inside the dict).
        related_model: SQLAlchemy mapped class for the related table.
        related_schema: Pydantic model for list items.
        related_pk_col: Single PK column name for junction joins where needed.
        related_pk_order: Optional tuple of all PK columns for ordering.

    Returns:
        Immutable spec suitable for :func:`list_relation_subresource_page`.

    Raises:
        ValueError: If ``sync`` is incomplete for its ``kind`` or ``kind`` is
            unknown.
    """

    kind = str(sync["kind"])
    parent_pk_attrs = tuple(str(x) for x in sync["parent_pk_attrs"])

    # Dispatch by relation shape and attach ORM / FK fields from ``sync``.
    if kind == "o2m_fk":
        fk = str(sync["child_fk_col"])
        return RelationListSpec(
            kind=kind,
            parent_pk_attrs=parent_pk_attrs,
            related_model=related_model,
            related_schema=related_schema,
            related_pk_col=related_pk_col,
            related_pk_order=related_pk_order,
            child_fk_col=fk,
        )
    if kind in ("m2m", "o2m_bridge"):
        if sync.get("assoc_model") is None:
            raise ValueError("m2m sync requires assoc_model")
        p_cols = tuple(str(x) for x in (sync.get("parent_fk_cols") or ()))
        rfk = sync.get("related_fk_col")
        if not p_cols or rfk is None:
            raise ValueError(
                "m2m sync requires parent_fk_cols and related_fk_col"
            )
        return RelationListSpec(
            kind=kind,
            parent_pk_attrs=parent_pk_attrs,
            related_model=related_model,
            related_schema=related_schema,
            related_pk_col=related_pk_col,
            related_pk_order=related_pk_order,
            assoc_model=sync["assoc_model"],
            parent_fk_cols=p_cols,
            related_fk_col=str(rfk),
        )
    if kind == "o2m_child_rows":
        p_cols = tuple(str(x) for x in (sync.get("parent_fk_cols") or ()))
        if len(p_cols) != 1:
            raise ValueError("o2m_child_rows expects a single parent FK column")
        return RelationListSpec(
            kind=kind,
            parent_pk_attrs=parent_pk_attrs,
            related_model=related_model,
            related_schema=related_schema,
            related_pk_col=related_pk_col,
            related_pk_order=related_pk_order,
            child_fk_col=p_cols[0],
        )
    raise ValueError("unsupported sync kind %r" % (kind,))


def column_values_for_ex(row: Any) -> dict[str, Any]:
    """Expose scalar ORM columns as a dict for Pydantic validation.

    Args:
        row: Loaded SQLAlchemy mapped instance.

    Returns:
        Mapping from mapped column attribute names to Python values.
    """

    # One entry per mapped column; relationship collections are omitted.
    mapper = inspect(row).mapper
    return {attr.key: getattr(row, attr.key) for attr in mapper.column_attrs}


def ex_model_from_orm_columns(row: Any, ex_model: type[TEx]) -> TEx:
    """Construct an ``*Ex`` DTO from ORM scalars only (no nested lists).

    Args:
        row: SQLAlchemy row for the root resource.
        ex_model: Target ``*Ex`` Pydantic class.

    Returns:
        Validated ``ex_model`` instance with relation list fields at defaults.
    """

    return ex_model.model_validate(column_values_for_ex(row))


def filter_items_to_clauses(
    model: type[Any], items: list[FilterItem]
) -> list[Any]:
    """Translate JSON filter items into SQLAlchemy boolean AND clauses.

    Args:
        model: ORM mapped class whose columns are referenced by ``FilterItem``.
        items: Parsed filter items (field, op, value).

    Returns:
        List of SQLAlchemy expressions combined with :func:`sqlalchemy.and_`.

    Raises:
        ValueError: If an operator or field name is not supported on ``model``.
    """

    out: list[Any] = []

    # Each item becomes one predicate; unknown op or column raises.
    for it in items:
        ff = it.as_op
        fi = filter_op_registry.get(ff.op)
        if fi is None:
            raise ValueError(
                "unknown filter op %r for field %r" % (ff.op, ff.fld)
            )
        if not hasattr(model, ff.fld):
            raise ValueError(
                "unknown field %r on %s" % (ff.fld, model.__name__)
            )
        col = getattr(model, ff.fld)
        out.append(fi.predicate(col, ff.vl))
    return out


def sort_items_to_order_by(
    model: type[Any],
    sort_items: list[SortItem],
    pk_names: Sequence[str],
) -> list[Any]:
    """Build SQLAlchemy ``ORDER BY`` with stable PK tie-breakers.

    When ``sort_items`` is empty, order by ``pk_names`` ascending only. When it
    is non-empty, apply requested columns first, then append any PK columns not
    yet used so paging is deterministic.

    Args:
        model: ORM mapped class providing column descriptors.
        sort_items: Client sort directives (may be empty).
        pk_names: ORM attribute names forming the default / tie-break order.

    Returns:
        List of unary ``asc()`` / ``desc()`` column clauses.

    Raises:
        ValueError: If a sort field is not a mapped column on ``model``.
    """

    cols: list[Any] = []

    # Default path: no explicit sort, use primary key columns only.
    if not sort_items:
        for pk in pk_names:
            cols.append(getattr(model, pk).asc())
        return cols

    # Explicit sort keys first, then any PK columns not already listed.
    seen: set[str] = set()
    for s in sort_items:
        if not hasattr(model, s.attr):
            raise ValueError(
                "unknown sort field %r on %s" % (s.attr, model.__name__)
            )
        c = getattr(model, s.attr)
        cols.append(c.asc() if s.order == "asc" else c.desc())
        seen.add(s.attr)
    for pk in pk_names:
        if pk not in seen:
            cols.append(getattr(model, pk).asc())
    return cols


def select_paged_rows(
    db: Session,
    model: type[Any],
    *,
    filters: list[FilterItem],
    sort: list[SortItem],
    pk_names: Sequence[str],
    offset: int,
    limit: int,
) -> tuple[int, list[Any]]:
    """Return total row count and one page of ORM instances for a root list.

    Args:
        db: Open SQLAlchemy session.
        model: Root ORM mapped class.
        filters: Parsed filter list (may be empty).
        sort: Parsed sort list (may be empty; PK tie-break still applied).
        pk_names: PK column names on ``model`` for ordering.
        offset: Zero-based row offset.
        limit: Maximum rows to return (page size).

    Returns:
        ``(total, rows)`` where ``total`` counts matching rows and ``rows`` is
        the current page.
    """

    clauses = filter_items_to_clauses(model, filters)

    # With filters: count and select under the same WHERE.
    if clauses:
        where = and_(*clauses)
        total = int(
            db.scalar(select(func.count()).select_from(model).where(where)) or 0
        )
        order_by = sort_items_to_order_by(model, sort, pk_names)
        stmt: Select[Any] = (
            select(model)
            .where(where)
            .order_by(*order_by)
            .offset(offset)
            .limit(limit)
        )
    else:
        # No filters: full-table count, ordered scan with offset/limit.
        total = int(db.scalar(select(func.count()).select_from(model)) or 0)
        order_by = sort_items_to_order_by(model, sort, pk_names)
        stmt = select(model).order_by(*order_by).offset(offset).limit(limit)

    rows = list(db.scalars(stmt).unique().all())
    return total, rows


def list_relation_subresource_page(
    db: Session,
    *,
    parent_row: Any,
    spec: RelationListSpec,
    filters: list[FilterItem],
    sort: list[SortItem],
    offset: int,
    limit: int,
) -> PagedList[BaseModel]:
    """Load one page of related rows for a single parent (nested list).

    Supports ``o2m_fk`` (FK on child), ``m2m`` / ``o2m_bridge`` (via junction),
    and ``o2m_child_rows`` (child rows keyed by parent FK). Items are validated
    with ``spec.related_schema``; return type is :class:`PagedList` of
    :class:`pydantic.BaseModel` because the concrete schema varies by spec.

    Args:
        db: Open SQLAlchemy session.
        parent_row: ORM instance of the parent resource (provides PK values).
        spec: Frozen relation metadata including ORM and Pydantic types.
        filters: Filter items scoped to ``spec.related_model``.
        sort: Sort items scoped to ``spec.related_model``.
        offset: Zero-based offset within the related set.
        limit: Maximum related rows (inner list page size).

    Returns:
        :class:`PagedList` whose ``items`` are ``spec.related_schema`` instances.

    Raises:
        ValueError: If ``spec`` is inconsistent with ``kind`` or ``kind`` is
            unsupported.
    """

    rel = spec.related_model
    schema = spec.related_schema
    pkc = spec.related_pk_col
    pk_order = spec.related_pk_order if spec.related_pk_order else (pkc,)

    # One-to-many: child rows reference parent via a single FK column.
    if spec.kind == "o2m_fk":
        if spec.child_fk_col is None or len(spec.parent_pk_attrs) != 1:
            raise ValueError("invalid o2m_fk RelationListSpec")
        p_val = getattr(parent_row, spec.parent_pk_attrs[0])
        fk = getattr(rel, spec.child_fk_col)
        base = [fk == p_val]
        base.extend(filter_items_to_clauses(rel, filters))
        where = and_(*base)
        total = int(
            db.scalar(select(func.count()).select_from(rel).where(where)) or 0
        )
        order_by = sort_items_to_order_by(rel, sort, pk_order)
        stmt = (
            select(rel)
            .where(where)
            .order_by(*order_by)
            .offset(offset)
            .limit(limit)
        )
    elif spec.kind in ("m2m", "o2m_bridge"):
        # Many-to-many (or bridge): join related through association table.
        if (
            spec.assoc_model is None
            or spec.parent_fk_cols is None
            or spec.related_fk_col is None
        ):
            raise ValueError("invalid m2m RelationListSpec")
        assoc = spec.assoc_model
        parent_clauses = [
            getattr(assoc, pc) == getattr(parent_row, pa)
            for pc, pa in zip(spec.parent_fk_cols, spec.parent_pk_attrs)
        ]
        join_on = getattr(assoc, spec.related_fk_col) == getattr(rel, pkc)
        rel_clauses = filter_items_to_clauses(rel, filters)
        where = (
            and_(*parent_clauses, *rel_clauses)
            if rel_clauses
            else and_(*parent_clauses)
        )
        base_stmt = select(rel).join(assoc, join_on).where(where)
        subq = base_stmt.subquery()
        total = int(db.scalar(select(func.count()).select_from(subq)) or 0)
        order_by = sort_items_to_order_by(rel, sort, pk_order)
        stmt = base_stmt.order_by(*order_by).offset(offset).limit(limit)
    elif spec.kind == "o2m_child_rows":
        # Child table rows: filter by FK to parent, no junction join.
        if spec.child_fk_col is None or len(spec.parent_pk_attrs) != 1:
            raise ValueError("invalid o2m_child_rows RelationListSpec")
        p_val = getattr(parent_row, spec.parent_pk_attrs[0])
        fk = getattr(rel, spec.child_fk_col)
        base = [fk == p_val]
        base.extend(filter_items_to_clauses(rel, filters))
        where = and_(*base)
        total = int(
            db.scalar(select(func.count()).select_from(rel).where(where)) or 0
        )
        order_by = sort_items_to_order_by(rel, sort, pk_order)
        stmt = (
            select(rel)
            .where(where)
            .order_by(*order_by)
            .offset(offset)
            .limit(limit)
        )
    else:
        raise ValueError("unsupported kind %r" % (spec.kind,))

    # Materialize ORM rows and map scalars to the declared Pydantic list item.
    rows = list(db.scalars(stmt).unique().all())
    items = [schema.model_validate(column_values_for_ex(r)) for r in rows]
    return PagedList(
        total=total,
        offset=offset,
        page_size=limit,
        items=items,
    )


def hydrate_ex_inner_lists(
    db: Session,
    *,
    parent_row: Any,
    ex: TEx,
    inner_page: int,
    inner_filters: dict[str, list[FilterItem]],
    inner_sort: dict[str, list[SortItem]],
    inner_specs: Sequence[tuple[str, RelationListSpec]],
) -> TEx:
    """Populate ``PagedList`` fields on one ``*Ex`` from the parent ORM row.

    Each ``(attr, spec)`` loads ``inner_page`` related rows into ``ex.attr``.
    When ``inner_page`` is zero or ``inner_specs`` is empty, ``ex`` is returned
    unchanged.

    Args:
        db: Open SQLAlchemy session.
        parent_row: ORM row matching ``ex`` (same PK).
        ex: Partial ``*Ex`` built from ``parent_row`` scalars only.
        inner_page: Maximum rows per nested list (``<= 0`` disables hydration).
        inner_filters: Per-relation filter lists keyed by ``attr`` name.
        inner_sort: Per-relation sort lists keyed by ``attr`` name.
        inner_specs: Ordered ``(relation_field_name, RelationListSpec)`` pairs.

    Returns:
        Copy of ``ex`` with nested ``PagedList`` fields set, or ``ex`` if nothing
        was loaded.

    Raises:
        ValueError: Re-raised after logging if a nested list query is invalid.
    """

    if inner_page <= 0 or not inner_specs:
        return ex

    # Load each configured inner list and merge into a model_copy update.
    updates: dict[str, Any] = {}
    for attr, rspec in inner_specs:
        try:
            pl = list_relation_subresource_page(
                db,
                parent_row=parent_row,
                spec=rspec,
                filters=inner_filters.get(attr, []),
                sort=inner_sort.get(attr, []),
                offset=0,
                limit=inner_page,
            )
        except ValueError as exc:
            logger.error(
                "inner list %s failed for parent %s: %s",
                attr,
                parent_row,
                exc,
                exc_info=True,
            )
            raise
        updates[attr] = pl
    return ex.model_copy(update=updates) if updates else ex


def list_root_ex_page(
    db: Session,
    orm_model: type[Any],
    ex_model: type[TEx],
    *,
    pk_names: Sequence[str],
    offset: int,
    page_size: int,
    filters: list[FilterItem],
    sort: list[SortItem],
    inner_page: int,
    inner_filters: dict[str, list[FilterItem]],
    inner_sort: dict[str, list[SortItem]],
    inner_specs: Sequence[tuple[str, RelationListSpec]],
) -> PagedList[TEx]:
    """List root resources as ``PagedList`` of ``*Ex`` with optional inner pages.

    Loads one page of ``orm_model`` rows, maps each to ``ex_model``, then when
    ``inner_page > 0`` fills nested relation lists via
    :func:`hydrate_ex_inner_lists`.

    Args:
        db: Open SQLAlchemy session.
        orm_model: Root ORM mapped class.
        ex_model: Root ``*Ex`` Pydantic class.
        pk_names: PK column names on ``orm_model`` for root list ordering.
        offset: Zero-based offset into the filtered root set.
        page_size: Root list page size.
        filters: Root-level filter items.
        sort: Root-level sort items.
        inner_page: Inner list page size (``<= 0`` skips nested loads).
        inner_filters: Nested list filters keyed by relation attribute name.
        inner_sort: Nested list sorts keyed by relation attribute name.
        inner_specs: Nested list specs in field order.

    Returns:
        :class:`PagedList` of hydrated ``ex_model`` instances.
    """

    total, rows = select_paged_rows(
        db,
        orm_model,
        filters=filters,
        sort=sort,
        pk_names=pk_names,
        offset=offset,
        limit=page_size,
    )

    # Build each Ex from ORM columns, optionally attaching inner PagedLists.
    items: list[TEx] = []
    for row in rows:
        ex = ex_model_from_orm_columns(row, ex_model)
        if inner_page > 0 and inner_specs:
            ex = hydrate_ex_inner_lists(
                db,
                parent_row=row,
                ex=ex,
                inner_page=inner_page,
                inner_filters=inner_filters,
                inner_sort=inner_sort,
                inner_specs=inner_specs,
            )
        items.append(ex)
    return PagedList(
        total=total,
        offset=offset,
        page_size=page_size,
        items=items,
    )
