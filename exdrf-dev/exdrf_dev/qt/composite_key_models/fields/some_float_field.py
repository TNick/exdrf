# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.
from typing import TYPE_CHECKING, Any, Dict

from attrs import define, field
from exdrf_qt.models.fields import QtFloatField
from PyQt5.QtCore import Qt

if TYPE_CHECKING:
    from exdrf_dev.db.models import CompositeKeyModel  # noqa: F401


@define
class SomeFloatField(QtFloatField["CompositeKeyModel"]):
    """A floating-point number.."""

    name: str = field(default="some_float", init=False)
    title: str = field(default="Some Float")
    description: str = field(default=("A floating-point number."))
    visible: bool = field(default=True)
    nullable: bool = field(default=True)
    read_only: bool = field(default=False)
    resizable: bool = field(default=True)
    sortable: bool = field(default=True)
    filterable: bool = field(default=True)
    exportable: bool = field(default=True)
    qsearch: bool = field(default=True)

    min: float = field(default=0.0)
    max: float = field(default=100.0)
    precision: int = field(default=2)
    scale: int = field(default=2)
    unit: str = field(default="units")
    unit_symbol: str = field(default="u")

    def values(self, item: "CompositeKeyModel") -> Dict[Qt.ItemDataRole, Any]:
        return self.expand_value(item.some_float)
