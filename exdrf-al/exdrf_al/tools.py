import logging
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.orm import (
    InstrumentedAttribute,
    RelationshipProperty,
    class_mapper,
)

if TYPE_CHECKING:
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
