"""Result of applying an import plan."""

from __future__ import annotations

from attrs import define, field


@define
class ApplyResult:
    """Result of applying an import plan.

    Attributes:
        inserted: Number of rows inserted.
        updated: Number of rows updated.
        deferred: Number of deferred foreign key updates applied.
        placeholder_to_id: Mapping from (table_name, placeholder_string)
            to allocated integer ID. Only includes placeholders that were
            resolved during import.
    """

    inserted: int = 0
    updated: int = 0
    deferred: int = 0
    placeholder_to_id: dict[tuple[str, str], int] = field(factory=dict)
