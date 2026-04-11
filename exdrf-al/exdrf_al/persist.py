"""SQLAlchemy helpers for persisting ORM rows and simple relation lists."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any, Iterator, TypeVar

from sqlalchemy import and_, delete, insert, select, update
from sqlalchemy.orm import Session

T = TypeVar("T")


class RowNotFound(LookupError):
    """Raised when :func:`fetch_one_strict` finds no matching row."""


def fetch_one_strict(
    db: Session,
    model: type[Any],
    *pk_attr_value: tuple[str, Any],
) -> Any:
    """Load one ORM row by primary key values or raise :class:`RowNotFound`.

    Args:
        db: Active SQLAlchemy session.
        model: Declarative ORM class.
        *pk_attr_value: Each pair is ``(column_name, value)`` for one PK
            column (single or composite, in order).

    Returns:
        The matching ORM instance.

    Raises:
        RowNotFound: When no row matches.
        ValueError: When no primary-key pairs are passed.
    """

    if not pk_attr_value:
        raise ValueError("pk_attr_value must not be empty.")
    clauses = tuple(
        getattr(model, name) == value for name, value in pk_attr_value
    )
    if len(clauses) == 1:
        stmt = select(model).where(clauses[0])
    else:
        stmt = select(model).where(and_(*clauses))
    row = db.scalars(stmt).first()
    if row is None:
        raise RowNotFound("no row matches primary key")
    return row


def apply_payload_attrs(
    model_or_row: type[Any] | Any,
    payload: Mapping[str, Any],
    *attr_names: str,
) -> Any:
    """Create a new row or patch attributes from ``payload``.

    When ``model_or_row`` is a declarative class, a new instance is created,
    attributes listed in ``attr_names`` are copied from ``payload``, and that
    instance is returned. When it is an existing instance, attributes are set
    in place and the same object is returned.

    Args:
        model_or_row: ORM class to instantiate, or row to mutate.
        payload: Mapping from a Pydantic ``model_dump`` (often partial).
        *attr_names: Attribute names to assign when the key exists in
            ``payload`` (value may be ``None``).

    Returns:
        The new or updated ORM instance.
    """

    row = model_or_row() if isinstance(model_or_row, type) else model_or_row
    for name in attr_names:
        if name in payload:
            setattr(row, name, payload[name])
    return row


def persist_row_as_ex(
    db: Session,
    row: Any,
    ex_model: type[Any],
    *,
    add: bool = False,
) -> Any:
    """Flush, refresh, and build the public ``Ex`` DTO for ``row``.

    Args:
        db: Active SQLAlchemy session.
        row: ORM instance (new or already loaded).
        ex_model: Pydantic ``Ex`` class for this resource.
        add: When ``True``, call ``db.add(row)`` before flush (new rows).

    Returns:
        ``ex_model`` built with ``model_validate(..., from_attributes=True)``.
    """

    if add:
        db.add(row)
    db.flush()
    db.refresh(row)
    return ex_model.model_validate(row, from_attributes=True)


@contextmanager
def persist_row_as_ex_cm(
    db: Session,
    row: Any,
    ex_model: type[Any],
    *,
    add: bool = False,
) -> Iterator[SimpleNamespace]:
    """Flush once, run relation work, then flush again and build ``Ex``.

    Yields a namespace with ``row`` (live ORM instance); after the ``with``
    block, ``ex`` is set on the same namespace from a final flush/refresh.

    Args:
        db: Active SQLAlchemy session.
        row: ORM instance (new or already loaded).
        ex_model: Pydantic ``Ex`` class for this resource.
        add: When ``True``, call ``db.add(row)`` before the first flush.

    Yields:
        ``SimpleNamespace(row=..., ex=None)``; after the block, ``ex`` is
        filled with the validated DTO.
    """

    holder = SimpleNamespace(row=row, ex=None)
    if add:
        db.add(holder.row)
    db.flush()
    db.refresh(holder.row)
    try:
        yield holder
    finally:
        db.flush()
        db.refresh(holder.row)
        holder.ex = ex_model.model_validate(
            holder.row,
            from_attributes=True,
        )


def _parent_pk_values(
    parent_row: Any, parent_pk_attrs: tuple[str, ...]
) -> tuple:
    return tuple(getattr(parent_row, a) for a in parent_pk_attrs)


def sync_m2m_list_replace(
    db: Session,
    assoc_model: type[Any],
    parent_fk_cols: tuple[str, ...],
    related_fk_col: str,
    parent_row: Any,
    parent_pk_attrs: tuple[str, ...],
    items: list[Any] | None,
) -> None:
    """Full-replace a many-to-many link set using Core delete + insert.

    Deletes all ``assoc_model`` rows matching the parent primary key(s), then
    inserts one row per entry in ``items``. Each entry is either an ``int``
    (related single-column PK) or a ``dict`` of association column names onto
    values; parent FK columns are always taken from ``parent_row``.

    Args:
        db: Active SQLAlchemy session.
        assoc_model: Declarative class for the association / junction table.
        parent_fk_cols: Association column names that reference the parent
            (same length and order as ``parent_pk_attrs``).
        related_fk_col: Association column for the related PK when ``items`` are
            plain ints; dict items must include related-side columns when the
            related PK is composite.
        parent_row: Loaded parent ORM instance (PKs populated).
        parent_pk_attrs: Parent PK attribute names on ``parent_row``.
        items: New related keys, or ``None`` / empty to clear only.
    """

    pvals = _parent_pk_values(parent_row, parent_pk_attrs)
    del_clauses = tuple(
        getattr(assoc_model, col) == val
        for col, val in zip(parent_fk_cols, pvals)
    )
    db.execute(delete(assoc_model).where(and_(*del_clauses)))
    if not items:
        return
    for it in items:
        row_map: dict[str, Any] = {}
        for col, val in zip(parent_fk_cols, pvals):
            row_map[col] = val
        if isinstance(it, dict):
            row_map.update(it)
        else:
            if not related_fk_col:
                raise ValueError(
                    "sync_m2m_list_replace requires dict items when the "
                    "related primary key is composite.",
                )
            row_map[related_fk_col] = it
        db.execute(insert(assoc_model).values(**row_map))


def sync_o2m_fk_list_replace(
    db: Session,
    child_model: type[Any],
    child_fk_col: str,
    child_pk_col: str,
    parent_row: Any,
    parent_pk_attrs: tuple[str, ...],
    child_ids: list[int] | None,
) -> None:
    """Full-replace one-to-many ownership via FK on the child (Core UPDATE).

    First clears ``child_fk_col`` for every child that pointed at this parent,
    then assigns ``child_fk_col`` for rows whose ``child_pk_col`` is in
    ``child_ids``.

    Args:
        db: Active SQLAlchemy session.
        child_model: Declarative child class holding ``child_fk_col``.
        child_fk_col: Foreign-key column on the child toward the parent.
        child_pk_col: Primary-key column on the child (single column).
        parent_row: Loaded parent ORM instance.
        parent_pk_attrs: Parent PK attribute names (length 1 for simple FK).
        child_ids: Child PK values to attach; ``None`` or empty clears all.
    """

    if len(parent_pk_attrs) != 1:
        raise ValueError(
            "sync_o2m_fk_list_replace supports a single-column parent PK only.",
        )
    pval = getattr(parent_row, parent_pk_attrs[0])
    fk_attr = getattr(child_model, child_fk_col)
    pk_attr = getattr(child_model, child_pk_col)

    # Detach every child currently pointing at this parent (full replace).
    db.execute(
        update(child_model).where(fk_attr == pval).values({child_fk_col: None})
    )
    if not child_ids:
        return
    db.execute(
        update(child_model)
        .where(pk_attr.in_(child_ids))
        .values({child_fk_col: pval})
    )
