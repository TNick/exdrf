# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.
from typing import TYPE_CHECKING, Any, Dict

from attrs import define, field
from exdrf_qt.models.fields import QtStringField
from PyQt5.QtCore import Qt

if TYPE_CHECKING:
    from exdrf_dev.db.models import CompositeKeyModel  # noqa: F401


@define
class SomeEnumField(QtStringField["CompositeKeyModel"]):
    """An enum value representing status.."""

    name: str = field(default="some_enum", init=False)
    title: str = field(default="Some Enum")
    description: str = field(default=("An enum value representing status."))
    visible: bool = field(default=True)
    nullable: bool = field(default=True)
    read_only: bool = field(default=False)
    resizable: bool = field(default=True)
    sortable: bool = field(default=True)
    filterable: bool = field(default=True)
    exportable: bool = field(default=True)
    qsearch: bool = field(default=True)

    multiline: bool = field(default=False)
    max_length: int = field(default=10)

    def values(self, item: "CompositeKeyModel") -> Dict[Qt.ItemDataRole, Any]:
        return self.expand_value(item.some_enum)
