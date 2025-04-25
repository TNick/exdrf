# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.
from typing import TYPE_CHECKING, Any, Dict

from attrs import define, field
from exdrf_qt.models.fields import QtStringField
from PyQt5.QtCore import Qt

if TYPE_CHECKING:
    from exdrf_dev.db.models import RelatedItem  # noqa: F401


@define
class CompKeyPart1Field(QtStringField["RelatedItem"]):
    """Foreign key part 1 referencing CompositeKeyModel.."""

    name: str = field(default="comp_key_part1", init=False)
    title: str = field(default="Comp Key Part1")
    description: str = field(
        default=("Foreign key part 1 referencing CompositeKeyModel.")
    )
    visible: bool = field(default=True)
    nullable: bool = field(default=False)
    read_only: bool = field(default=False)
    resizable: bool = field(default=True)
    sortable: bool = field(default=True)
    filterable: bool = field(default=True)
    exportable: bool = field(default=True)
    qsearch: bool = field(default=True)

    multiline: bool = field(default=False)
    max_length: int = field(default=50)

    def values(self, item: "RelatedItem") -> Dict[Qt.ItemDataRole, Any]:
        return self.expand_value(item.comp_key_part1)
