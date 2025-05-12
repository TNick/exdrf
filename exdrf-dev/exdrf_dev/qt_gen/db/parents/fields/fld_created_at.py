# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/field.py.j2
# Don't change it manually.
from datetime import date, datetime
from typing import TYPE_CHECKING

from attrs import define, field
from exdrf_qt.models.fields import QtDateTimeField

if TYPE_CHECKING:
    from exdrf_dev.db.api import Parent  # noqa: F401


@define
class CreatedAtField(QtDateTimeField["Parent"]):
    """Timestamp when the parent was created."""

    name: str = field(default="created_at", init=False)
    title: str = field(default="Created At")
    description: str = field(default=("Timestamp when the parent was created."))
    category: str = field(default="general")
    nullable: bool = field(default=False)
    min: datetime = field(default=date(2020, 1, 1))
    max: datetime = field(default=date(2030, 12, 31))
    preferred_width: int = field(default=100)
