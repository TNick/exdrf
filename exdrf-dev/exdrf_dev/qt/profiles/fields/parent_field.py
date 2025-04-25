# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.
from typing import TYPE_CHECKING, Any, Dict

from attrs import define, field
from exdrf_qt.models.fields import QtRefOneToOneField
from PyQt5.QtCore import Qt

if TYPE_CHECKING:
    from exdrf.resource import ExResource  # noqa: F401

    from exdrf_dev.db.models import Profile  # noqa: F401


@define
class ParentField(QtRefOneToOneField["Profile"]):
    """ """

    name: str = field(default="parent", init=False)
    title: str = field(default="Parent")
    visible: bool = field(default=True)
    nullable: bool = field(default=True)
    read_only: bool = field(default=False)
    resizable: bool = field(default=True)
    sortable: bool = field(default=True)
    filterable: bool = field(default=True)
    exportable: bool = field(default=True)
    qsearch: bool = field(default=True)
    ts_type: str = field(default="one-to-one")
    py_type: str = field(default="")
    ref: "ExResource" = field(default=None, repr=False)

    def values(self, item: "Profile") -> Dict[Qt.ItemDataRole, Any]:
        return self.expand_value(item.parent)
