# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.
from datetime import date
from typing import TYPE_CHECKING, Any, Dict

from attrs import define, field
from exdrf_qt.models.fields import QtDateField
from PyQt5.QtCore import Qt

if TYPE_CHECKING:
    from exdrf_dev.db.models import CompositeKeyModel  # noqa: F401


@define
class SomeDateField(QtDateField["CompositeKeyModel"]):
    """A date value.."""

    name: str = field(default="some_date", init=False)
    title: str = field(default="Some Date")
    description: str = field(default=("A date value."))
    visible: bool = field(default=True)
    nullable: bool = field(default=True)
    read_only: bool = field(default=False)
    resizable: bool = field(default=True)
    sortable: bool = field(default=True)
    filterable: bool = field(default=True)
    exportable: bool = field(default=True)
    qsearch: bool = field(default=True)

    min: date = field(default=date(2020, 1, 1))
    max: date = field(default=date(2021, 12, 31))

    def values(self, item: "CompositeKeyModel") -> Dict[Qt.ItemDataRole, Any]:
        return self.expand_value(item.some_date)
