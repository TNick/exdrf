# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.
from typing import TYPE_CHECKING

from attrs import define, field
from exdrf_qt.models.fields import QtIntegerField

if TYPE_CHECKING:
    from exdrf_dev.db.models import ParentTagAssociation  # noqa: F401


@define
class ParentIdField(QtIntegerField["ParentTagAssociation"]):
    """Foreign key to the parents table.."""

    name: str = field(default="parent_id", init=False)
    title: str = field(default="Parent Id")
    description: str = field(default=("Foreign key to the parents table."))
    primary: bool = field(default=True)
    visible: bool = field(default=True)
    nullable: bool = field(default=False)
    read_only: bool = field(default=False)
    resizable: bool = field(default=True)
    sortable: bool = field(default=True)
    filterable: bool = field(default=True)
    exportable: bool = field(default=True)
    qsearch: bool = field(default=True)
