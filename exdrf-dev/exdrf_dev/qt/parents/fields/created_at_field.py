# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.
from datetime import datetime
from typing import TYPE_CHECKING

from attrs import define, field
from exdrf_qt.models.fields import QtDateTimeField

if TYPE_CHECKING:
    from exdrf_dev.db.models import Parent  # noqa: F401


@define
class CreatedAtField(QtDateTimeField["Parent"]):
    """Timestamp when the parent was created.."""

    name: str = field(default="created_at", init=False)
    title: str = field(default="Created At")
    description: str = field(default=("Timestamp when the parent was created."))
    visible: bool = field(default=True)
    nullable: bool = field(default=False)
    read_only: bool = field(default=False)
    resizable: bool = field(default=True)
    sortable: bool = field(default=True)
    filterable: bool = field(default=True)
    exportable: bool = field(default=True)
    qsearch: bool = field(default=True)

    min: datetime = field(default=datetime(2020, 1, 1, 00, 00, 00))
    max: datetime = field(default=datetime(2030, 1, 1, 00, 00, 00))
