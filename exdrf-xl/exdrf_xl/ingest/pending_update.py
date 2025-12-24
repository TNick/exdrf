"""Pending update representation for deferred placeholder replacements."""

from __future__ import annotations

from typing import Any, TypeAlias

from attrs import define

DbRecord: TypeAlias = Any


@define
class PendingUpdate:
    """A deferred placeholder replacement.

    Attributes:
        db_rec: The SQLAlchemy instance to update.
        column_name: Attribute name on the db record to set.
        placeholder: Placeholder token that must be resolved to an integer id.
        fk_table_name: Name of the table that the placeholder belongs to (the
            table referenced by the foreign key column).
    """

    db_rec: DbRecord | None
    column_name: str
    placeholder: str
    fk_table_name: str
