"""Label utilities for Parent records when referenced from Profile."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext

    from exdrf_dev.db.api import Parent


def parent_label(record: "Parent", ctx: "QtContext") -> str:
    """Return a display label for a Parent record.

    Args:
        record: The Parent record to label.
        ctx: The Qt context (unused but required by the API).

    Returns:
        A string label for the record.
    """
    if record is None:
        return ""
    return record.name or str(record.id)
