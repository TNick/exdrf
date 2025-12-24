"""Table difference representation for import plans."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from attrs import define

from .row_diff import RowDiff

if TYPE_CHECKING:
    from exdrf_xl.table import XlTable


@define(frozen=True)
class TableDiff:
    """Changes for a single table."""

    table: "XlTable[Any]"
    new_rows: tuple[RowDiff, ...]
    modified_rows: tuple[RowDiff, ...]
    existing_rows: int
    total_rows: int
