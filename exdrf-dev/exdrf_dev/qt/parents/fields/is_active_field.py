# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.
from typing import TYPE_CHECKING, Any, Dict

from attrs import define, field
from exdrf_qt.models.fields import QtBoolField
from PyQt5.QtCore import Qt

if TYPE_CHECKING:
    from exdrf_dev.db.models import Parent  # noqa: F401


@define
class IsActiveField(QtBoolField["Parent"]):
    """Flag indicating if the parent is active.."""

    name: str = field(default="is_active", init=False)
    title: str = field(default="Is Active")
    description: str = field(
        default=("Flag indicating if the parent is active.")
    )
    visible: bool = field(default=True)
    nullable: bool = field(default=False)
    read_only: bool = field(default=False)
    resizable: bool = field(default=False)
    sortable: bool = field(default=True)
    filterable: bool = field(default=True)
    exportable: bool = field(default=True)
    qsearch: bool = field(default=True)

    def values(self, item: "Parent") -> Dict[Qt.ItemDataRole, Any]:
        return self.expand_value(item.is_active)
