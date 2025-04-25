# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.
from typing import TYPE_CHECKING, Any, Dict

from attrs import define, field
from exdrf_qt.models.fields import QtStringField
from PyQt5.QtCore import Qt

if TYPE_CHECKING:
    from exdrf_dev.db.models import Child  # noqa: F401


@define
class DataField(QtStringField["Child"]):
    """Some data associated with the child.."""

    name: str = field(default="data", init=False)
    title: str = field(default="Data")
    description: str = field(default=("Some data associated with the child."))
    visible: bool = field(default=True)
    nullable: bool = field(default=True)
    read_only: bool = field(default=False)
    resizable: bool = field(default=True)
    sortable: bool = field(default=True)
    filterable: bool = field(default=True)
    exportable: bool = field(default=True)
    qsearch: bool = field(default=True)

    multiline: bool = field(default=True)
    min_length: int = field(default=1)
    max_length: int = field(default=200)

    def values(self, item: "Child") -> Dict[Qt.ItemDataRole, Any]:
        return self.expand_value(item.data)
