"""Import plan representation."""

from __future__ import annotations

from attrs import define

from .table_diff import TableDiff


@define(frozen=True)
class ImportPlan:
    """A prepared import plan, including detected modifications."""

    source_path: str
    tables: tuple[TableDiff, ...]

    @property
    def has_changes(self) -> bool:
        """Return True if the plan contains any changes."""
        return any(t.new_rows or t.modified_rows for t in self.tables)
