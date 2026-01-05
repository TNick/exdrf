import logging
from typing import TYPE_CHECKING

from sqlalchemy import and_, func, inspect, literal_column, select
from sqlalchemy.orm import (
    InstrumentedAttribute,
    RelationshipProperty,
    class_mapper,
)

if TYPE_CHECKING:
    from exdrf.constants import RecIdType
    from sqlalchemy.orm.session import Session


logger = logging.getLogger(__name__)


def count_relationship(session: "Session", record, rel_attr_name: str) -> int:
    # Get the mapper.
    cls = type(record)
    mapper = class_mapper(cls)  # type: ignore
    logger.debug(
        "Counting %s in model %s",
        rel_attr_name,
        cls.__name__,
    )

    # Check if the attribute exists.
    if not hasattr(cls, rel_attr_name):
        raise AttributeError(
            f"{cls.__name__} has no attribute '{rel_attr_name}'"
        )

    # Check if the attribute is a relationship.
    attr = getattr(cls, rel_attr_name)
    if not isinstance(attr, InstrumentedAttribute):
        raise TypeError(f"'{rel_attr_name}' is not a SQLAlchemy relationship")

    rel_prop: RelationshipProperty = mapper.get_property(  # type: ignore
        rel_attr_name
    )
    target_cls = rel_prop.mapper.class_

    # === One-to-many ===
    if rel_prop.secondary is None:  # type: ignore
        # Build WHERE clause from local-remote column pairs
        conditions = []
        for (
            local_col,
            remote_col,
        ) in rel_prop.local_remote_pairs:  # type: ignore
            value = getattr(record, local_col.name)
            conditions.append(remote_col == value)

        stmt = select(func.count()).select_from(target_cls).where(*conditions)
        return session.execute(stmt).scalar_one()

    # === Many-to-many ===
    else:
        assoc_table = rel_prop.secondary
        left_local_cols = []
        right_local_cols = []

        # Relationship from parent to association to target
        for (
            local_col,
            remote_col,
        ) in rel_prop.local_remote_pairs:  # type: ignore
            if local_col.table == cls.__table__:
                left_local_cols.append((local_col, remote_col))
            elif local_col.table == target_cls.__table__:
                # reverse order
                right_local_cols.append((remote_col, local_col))

        if not left_local_cols or not right_local_cols:
            raise NotImplementedError(
                "Cannot determine join keys for many-to-many relationship"
            )

        assoc_alias = assoc_table.alias()
        stmt = (
            select(func.count())
            .select_from(assoc_alias)
            .where(
                *[
                    assoc_alias.c[remote_col.name]
                    == getattr(record, local_col.name)
                    for local_col, remote_col in left_local_cols
                ]
            )
        )
        return session.execute(stmt).scalar_one()

    raise NotImplementedError("Unsupported relationship type")


def load_with_collection_counts_stm(orm_class, a_id: "RecIdType"):
    """
    Returns:
        (A_instance, {relationship_name: count, ...})

    Counts all collection relationships (rel.uselist == True):
      - many-to-many (secondary table)
      - one-to-many (FK on child table)
    Uses a single SQL statement and does not load the collections.
    """
    a_mapper = inspect(orm_class)
    pk_cols = list(a_mapper.primary_key)

    def _join_cond(subq, key_cols):
        # key_cols: list of columns in subq corresponding to pk_cols
        return and_(*[subq.c[k.name] == pk for k, pk in zip(key_cols, pk_cols)])

    stmt = select(orm_class)
    labels_by_rel = {}

    for rel in a_mapper.relationships:
        if not rel.uselist:
            continue  # only collections

        count_label = f"{rel.key}_count"

        # --- MANY-TO-MANY: count rows in secondary grouped by A's FK(s)
        if rel.secondary is not None:
            sec = rel.secondary

            # Map each PK col to the matching FK col in the secondary table
            sec_key_cols = []
            for pk in pk_cols:
                matches = [
                    c
                    for c in sec.c
                    if any(fk.column is pk for fk in c.foreign_keys)
                ]
                if len(matches) != 1:
                    sec_key_cols = []
                    break
                sec_key_cols.append(matches[0])

            if not sec_key_cols:
                raise ValueError(f"No matching key columns found for {rel.key}")

            subq = (
                select(
                    *[c.label(pk.name) for c, pk in zip(sec_key_cols, pk_cols)],
                    func.count(literal_column("*")).label(count_label),
                )
                .group_by(*sec_key_cols)
                .subquery()
            )

            stmt = stmt.outerjoin(subq, _join_cond(subq, pk_cols)).add_columns(
                func.coalesce(subq.c[count_label], 0).label(count_label)
            )
            labels_by_rel[rel.key] = count_label
            continue

        # --- ONE-TO-MANY: count child rows grouped by child FK(s) that point
        # to A's PK(s) relationship.foreign_keys are the child-side FK columns
        # participating in the join
        child_fk_cols = []
        for pk in pk_cols:
            matches = []
            for fk_col in rel.foreign_keys:
                for fk in fk_col.foreign_keys:
                    if fk.column is pk:
                        matches.append(fk_col)
            if len(matches) != 1:
                child_fk_cols = []
                raise ValueError(f"No matching key columns found for {rel.key}")
                break
            child_fk_cols.append(matches[0])

        if not child_fk_cols:
            raise ValueError(f"No matching key columns found for {rel.key}")

        child_table = rel.mapper.local_table

        subq = (
            select(
                *[c.label(pk.name) for c, pk in zip(child_fk_cols, pk_cols)],
                func.count(literal_column("*")).label(count_label),
            )
            .select_from(child_table)
            .group_by(*child_fk_cols)
            .subquery()
        )

        stmt = stmt.outerjoin(subq, _join_cond(subq, pk_cols)).add_columns(
            func.coalesce(subq.c[count_label], 0).label(count_label)
        )
        labels_by_rel[rel.key] = count_label

    a_list = [a_id] if isinstance(a_id, int) else list(a_id)
    if isinstance(a_id, int):
        if len(pk_cols) == 1:
            stmt = stmt.where(pk_cols[0] == a_id)
        else:
            raise ValueError(
                f"Multiple primary keys found for {orm_class.__name__}"
            )
    elif len(a_list) != len(pk_cols):
        raise ValueError(
            f"Number of primary keys for {orm_class.__name__} ({len(pk_cols)}) "
            f"is not the same as the length of the provided ID ({len(a_list)})"
        )
    else:
        stmt = stmt.where(and_(*[pk == a for pk, a in zip(pk_cols, a_list)]))
    return stmt, labels_by_rel


def load_with_collection_counts(
    session: "Session", orm_class, a_id: "RecIdType"
):
    """Load a record and count the number of related records in collections.

    Args:
        session: The SQLAlchemy session.
        orm_class: The SQLAlchemy model class.
        a_id: The primary key of the record to load.

    Returns:
        A tuple containing the record and a dictionary of relationship names and
        counts. If the record is not found, returns (None, None).
    """
    stmt, labels_by_rel = load_with_collection_counts_stm(orm_class, a_id)
    row = session.execute(stmt).one_or_none()
    if row is None:
        return None, None

    a_obj = row[0]
    counts = {
        rel_name: getattr(row, label)
        for rel_name, label in labels_by_rel.items()
    }
    return a_obj, counts
