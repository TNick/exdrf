# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/single_f.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING, Any, Dict

from attrs import define, field
from exdrf_qt.models.fields import QtStringField
from PyQt5.QtCore import Qt

if TYPE_CHECKING:
    from exdrf_dev.db.api import Profile  # noqa: F401


@define
class LabelField(QtStringField["Profile"]):
    """Provides a label for the record."""

    name: str = field(default="label", init=False)
    title: str = field(default="Label")
    description: str = field(default="A single label for the entire record")

    primary: bool = field(default=False)
    visible: bool = field(default=True)
    nullable: bool = field(default=False)
    read_only: bool = field(default=True)
    resizable: bool = field(default=True)
    sortable: bool = field(default=False)
    filterable: bool = field(default=False)
    exportable: bool = field(default=True)
    qsearch: bool = field(default=True)
    multiline: bool = field(default=False)

    def values(self, record: "Profile") -> Dict[Qt.ItemDataRole, Any]:
        return self.expand_value(
            (str("ID:") + str(record.id) + str(" Bio:") + str(record.bio)),
            EditRole=record.id,
        )
