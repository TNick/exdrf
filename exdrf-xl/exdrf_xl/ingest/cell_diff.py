"""Cell difference representation for import plans."""

from __future__ import annotations

from typing import Any

from attrs import define


@define(frozen=True)
class CellDiff:
    """A single-cell difference between the database and Excel."""

    column: str
    old_value: Any
    new_value: Any
