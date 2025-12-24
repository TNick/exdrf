"""Row difference representation for import plans."""

from __future__ import annotations

from typing import Any, TypeAlias

from attrs import define

from .cell_diff import CellDiff

XlRecord: TypeAlias = dict[str, Any]
DbRecord: TypeAlias = Any


@define(frozen=True)
class RowDiff:
    """Differences for a single row in a table."""

    table_name: str
    is_new: bool
    pk: dict[str, Any]
    xl_row: XlRecord
    db_rec: DbRecord | None
    diffs: tuple[CellDiff, ...]
