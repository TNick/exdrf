# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.
from typing import TYPE_CHECKING

from attrs import define, field
from exdrf.constants import RecIdType
from exdrf_qt.models.fields import QtRefOneToManyField

if TYPE_CHECKING:
    from exdrf.resource import ExResource  # noqa: F401

    from exdrf_dev.db.models import Child, Parent  # noqa: F401


@define
class ChildrenField(QtRefOneToManyField["Parent"]):
    """ """

    name: str = field(default="children", init=False)
    title: str = field(default="Children")
    visible: bool = field(default=True)
    nullable: bool = field(default=True)
    read_only: bool = field(default=False)
    resizable: bool = field(default=True)
    sortable: bool = field(default=True)
    filterable: bool = field(default=True)
    exportable: bool = field(default=True)
    qsearch: bool = field(default=True)
    ref: "ExResource" = field(default=None, repr=False)

    def part_id(self, item: "Child") -> RecIdType:
        """Compute the ID for one of the components of the field."""
        return item.id

    def part_label(self, item: "Child") -> str:
        """Compute the label for one of the components of the field."""
        return item.data if item.data else str(item.id)
