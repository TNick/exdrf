# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.
from typing import TYPE_CHECKING

from attrs import define, field
from exdrf_qt.models.fields import QtStringField

if TYPE_CHECKING:
    from exdrf_dev.db.models import Parent  # noqa: F401


@define
class NameField(QtStringField["Parent"]):
    """Name of the parent.."""

    name: str = field(default="name", init=False)
    title: str = field(default="Name")
    description: str = field(default=("Name of the parent."))
    visible: bool = field(default=True)
    nullable: bool = field(default=False)
    read_only: bool = field(default=False)
    resizable: bool = field(default=True)
    sortable: bool = field(default=True)
    filterable: bool = field(default=True)
    exportable: bool = field(default=True)
    qsearch: bool = field(default=True)

    multiline: bool = field(default=False)
    min_length: int = field(default=1)
    max_length: int = field(default=100)
