# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.
from typing import TYPE_CHECKING, Any, Dict

from attrs import define, field
from exdrf_qt.models.fields import QtIntegerField
from PyQt5.QtCore import Qt

if TYPE_CHECKING:
    from exdrf_dev.db.models import CompositeKeyModel  # noqa: F401


@define
class KeyPart2Field(QtIntegerField["CompositeKeyModel"]):
    """Second part of the composite primary key (integer).."""

    name: str = field(default="key_part2", init=False)
    title: str = field(default="Key Part2")
    description: str = field(
        default=("Second part of the composite primary key (integer).")
    )
    primary: bool = field(default=True)
    visible: bool = field(default=True)
    nullable: bool = field(default=False)
    read_only: bool = field(default=False)
    resizable: bool = field(default=True)
    sortable: bool = field(default=True)
    filterable: bool = field(default=True)
    exportable: bool = field(default=True)
    qsearch: bool = field(default=True)

    def values(self, item: "CompositeKeyModel") -> Dict[Qt.ItemDataRole, Any]:
        return self.expand_value(item.key_part2)
