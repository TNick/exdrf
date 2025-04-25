# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.
from typing import TYPE_CHECKING, Any, Dict

from attrs import define, field
from exdrf_qt.models.fields import QtBlobField
from PyQt5.QtCore import Qt

if TYPE_CHECKING:
    from exdrf_dev.db.models import CompositeKeyModel  # noqa: F401


@define
class SomeBinaryField(QtBlobField["CompositeKeyModel"]):
    """Binary data.."""

    name: str = field(default="some_binary", init=False)
    title: str = field(default="Some Binary")
    description: str = field(default=("Binary data."))
    visible: bool = field(default=False)
    nullable: bool = field(default=True)
    read_only: bool = field(default=False)
    resizable: bool = field(default=True)
    sortable: bool = field(default=False)
    filterable: bool = field(default=False)
    exportable: bool = field(default=True)
    qsearch: bool = field(default=True)

    def values(self, item: "CompositeKeyModel") -> Dict[Qt.ItemDataRole, Any]:
        return self.blob_values(item.some_binary)
