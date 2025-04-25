# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.
from typing import TYPE_CHECKING, Any, Dict

from attrs import define, field
from exdrf_qt.models.fields import QtStringField
from PyQt5.QtCore import Qt

if TYPE_CHECKING:
    from exdrf_dev.db.models import Profile  # noqa: F401


@define
class BioField(QtStringField["Profile"]):
    """Biography text for the profile.."""

    name: str = field(default="bio", init=False)
    title: str = field(default="Bio")
    description: str = field(default=("Biography text for the profile."))
    visible: bool = field(default=True)
    nullable: bool = field(default=True)
    read_only: bool = field(default=False)
    resizable: bool = field(default=True)
    sortable: bool = field(default=True)
    filterable: bool = field(default=True)
    exportable: bool = field(default=True)
    qsearch: bool = field(default=True)

    multiline: bool = field(default=False)

    def values(self, item: "Profile") -> Dict[Qt.ItemDataRole, Any]:
        return self.expand_value(item.bio)
