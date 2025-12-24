"""Helper functions for import planning and application."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from exdrf.constants import FIELD_TYPE_DT  # type: ignore[import]
from exdrf.field_types.date_time import UNKNOWN_DATETIME

if TYPE_CHECKING:
    from exdrf_xl.table import XlTable


def default_is_db_pk(value: Any) -> bool:
    """Return True when a value represents a database primary key.

    The current heuristic is intentionally simple and customizable by callers:
    - integers are considered database IDs
    - strings are considered placeholders for new records

    Note:
        `bool` is a subclass of `int` in Python. We exclude booleans.

    Args:
        value: Candidate primary key value.

    Returns:
        True if `value` is considered a DB primary key.
    """
    return isinstance(value, int) and not isinstance(value, bool)


def normalize_unknown_datetime(value: Any) -> Any:
    """Normalize unknown date-time sentinel to a canonical representation."""
    if isinstance(value, str) and value.strip().lower() == "x":
        return UNKNOWN_DATETIME
    if isinstance(value, datetime):
        if (
            value.year == 1000
            and value.month == 2
            and value.day == 3
            and value.hour == 4
            and value.minute == 5
            and value.second == 6
        ):
            return UNKNOWN_DATETIME
    return value


def is_datetime_type(type_name: Any) -> bool:
    """Return True if the column `type_name` represents a datetime."""
    return str(type_name) in ("datetime", FIELD_TYPE_DT)


def build_import_table_ref_map(
    tables: list["XlTable[Any]"],
) -> dict[str, str]:
    """Build a reference-name -> canonical table name mapping.

    Generated code may refer to other tables by `XlTable.xl_name` or by the
    `XlTable` subclass name (e.g. `Org`), depending on generator/template.
    This helper maps both to a canonical identifier (`XlTable.xl_name`) so the
    import logic can be robust.

    Args:
        tables: Tables included in the import plan.

    Returns:
        Mapping from reference names to canonical `XlTable.xl_name`.
    """
    ref_to_xl_name: dict[str, str] = {}
    for t in tables:
        ref_to_xl_name[t.xl_name] = t.xl_name
        ref_to_xl_name[t.__class__.__name__] = t.xl_name
    return ref_to_xl_name


def iter_chunks(items: list[Any], size: int) -> list[list[Any]]:
    """Split a list into consecutive chunks."""
    if size <= 0:
        raise ValueError("Invalid chunk size %r" % size)
    return [items[i : i + size] for i in range(0, len(items), size)]
