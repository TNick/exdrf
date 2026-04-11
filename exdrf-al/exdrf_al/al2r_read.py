"""SQLAlchemy reads for AL2R list endpoints (filters, sort, paging)."""

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
TRel = TypeVar("TRel", bound=BaseModel)


@dataclass(frozen=True)
class RelationListSpec:
    """ORM metadata for one to-many / M2M list (mirrors relation sync kinds).

    Attributes:
        kind: ``o2m_fk``, ``m2m``, ``o2m_bridge``, or ``o2m_child_rows``.
        parent_pk_attrs: Parent PK attribute names on the parent ORM class.
        related_model: ORM class for rows returned in ``PagedList.items``.
        related_schema: Pydantic read model (base ``Related``, not ``*Ex``).
        related_pk_col: Primary-key column name on ``related_model``.
        child_fk_col: For ``o2m_fk``, FK column on ``related_model`` toward parent.
        assoc_model: Junction ORM class for ``m2m`` / ``o2m_bridge``.
        parent_fk_cols: Junction columns referencing the parent (``m2m`` / …).
        related_fk_col: Junction column referencing ``related_model`` PK.
    """

    kind: str
    parent_pk_attrs: tuple[str, ...]
    related_model: type[Any]
    related_schema: type[BaseModel]
    related_pk_col: str
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
) -> RelationListSpec:
    """Build a :class:`RelationListSpec` from a relation sync dict plus ORM types.

    Args:
        sync: Dict from :func:`~exdrf_gen_al2r.relation_specs.build_al2r_relation_sync_specs`
            (string metadata only; no ORM classes inside).
        related_model: Mapped class for related rows.
        related_schema: Pydantic schema for list items.
        related_pk_col: PK column name on ``related_model``.

    Returns:
        Frozen spec for :func:`list_relation_subresource_page`.

    Raises:
        ValueError: If ``sync`` is missing required keys for its ``kind``.
    """

    kind = str(sync["kind"])
    parent_pk_attrs = tuple(str(x) for x in sync["parent_pk_attrs"])
    if kind == "o2m_fk":
        fk = str(sync["child_fk_col"])
        return RelationListSpec(
            kind=kind,
            parent_pk_attrs=parent_pk_attrs,
            related_model=related_model,
            related_schema=related_schema,
            related_pk_col=related_pk_col,
            child_fk_col=fk,
        )
    if kind in ("m2m", "o2m_bridge"):
        if sync.get("assoc_model") is None:
            raise ValueError("m2m sync requires assoc_model")
        pcols = tuple(str(x) for x in (sync.get("parent_fk_cols") or ()))
        rfk = sync.get("related_fk_col")
        if not pcols or rfk is None:
            raise ValueError(
                "m2m sync requires parent_fk_cols and related_fk_col"
            )
        return RelationListSpec(
            kind=kind,
            parent_pk_attrs=parent_pk_attrs,
            related_model=related_model,
            related_schema=related_schema,
            related_pk_col=related_pk_col,
            assoc_model=sync["assoc_model"],
            parent_fk_cols=pcols,
            related_fk_col=str(rfk),
        )
    if kind == "o2m_child_rows":
        pcols = tuple(str(x) for x in (sync.get("parent_fk_cols") or ()))
        if len(pcols) != 1:
            raise ValueError("o2m_child_rows expects a single parent FK column")
        return RelationListSpec(
            kind=kind,
            parent_pk_attrs=parent_pk_attrs,
            related_model=related_model,
            related_schema=related_schema,
            related_pk_col=related_pk_col,
            child_fk_col=pcols[0],
        )
    raise ValueError("unsupported sync kind %r" % (kind,))


def column_values_for_ex(row: Any) -> dict[str, Any]:
    """Map ORM mapped columns to a plain dict for Pydantic ``Ex`` / ``Related``."""

    mapper = inspect(row).mapper
    return {attr.key: getattr(row, attr.key) for attr in mapper.column_attrs}


def ex_model_from_orm_columns(row: Any, ex_model: type[TEx]) -> TEx:
    """Build an ``*Ex`` DTO from ORM columns only (default empty list relations)."""

    return ex_model.model_validate(column_values_for_ex(row))


def filter_items_to_clauses(
    model: type[Any], items: list[FilterItem]
) -> list[Any]:
    """Turn ``FilterItem`` rows into SQLAlchemy boolean clauses (AND)."""

    out: list[Any] = []
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
    """Build ``ORDER BY`` columns (stable tie-break using primary keys)."""

    cols: list[Any] = []
    if not sort_items:
        for pk in pk_names:
            cols.append(getattr(model, pk).asc())
        return cols
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
    """Count and load one page of ORM rows with filters and sort."""

    clauses = filter_items_to_clauses(model, filters)
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
) -> PagedList[TRel]:
    """Load ``PagedList[Related]`` for ``GET /…/{pk}/relation``."""

    rel = spec.related_model
    schema = spec.related_schema
    pkc = spec.related_pk_col
    if spec.kind == "o2m_fk":
        if spec.child_fk_col is None or len(spec.parent_pk_attrs) != 1:
            raise ValueError("invalid o2m_fk RelationListSpec")
        pval = getattr(parent_row, spec.parent_pk_attrs[0])
        fk = getattr(rel, spec.child_fk_col)
        base = [fk == pval]
        base.extend(filter_items_to_clauses(rel, filters))
        where = and_(*base)
        total = int(
            db.scalar(select(func.count()).select_from(rel).where(where)) or 0
        )
        order_by = sort_items_to_order_by(rel, sort, (pkc,))
        stmt = (
            select(rel)
            .where(where)
            .order_by(*order_by)
            .offset(offset)
            .limit(limit)
        )
    elif spec.kind in ("m2m", "o2m_bridge"):
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
        order_by = sort_items_to_order_by(rel, sort, (pkc,))
        stmt = base_stmt.order_by(*order_by).offset(offset).limit(limit)
    elif spec.kind == "o2m_child_rows":
        if spec.child_fk_col is None or len(spec.parent_pk_attrs) != 1:
            raise ValueError("invalid o2m_child_rows RelationListSpec")
        pval = getattr(parent_row, spec.parent_pk_attrs[0])
        fk = getattr(rel, spec.child_fk_col)
        base = [fk == pval]
        base.extend(filter_items_to_clauses(rel, filters))
        where = and_(*base)
        total = int(
            db.scalar(select(func.count()).select_from(rel).where(where)) or 0
        )
        order_by = sort_items_to_order_by(rel, sort, (pkc,))
        stmt = (
            select(rel)
            .where(where)
            .order_by(*order_by)
            .offset(offset)
            .limit(limit)
        )
    else:
        raise ValueError("unsupported kind %r" % (spec.kind,))
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
    """Fill ``PagedList`` relation fields on one ``Ex`` instance."""

    if inner_page <= 0 or not inner_specs:
        return ex
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
    """List root resources as ``PagedList[ModelEx]`` with optional inner pages."""

    total, rows = select_paged_rows(
        db,
        orm_model,
        filters=filters,
        sort=sort,
        pk_names=pk_names,
        offset=offset,
        limit=page_size,
    )
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
