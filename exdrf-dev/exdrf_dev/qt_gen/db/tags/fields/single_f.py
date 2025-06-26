# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> c/m/single_f.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING, Any, Dict

from attrs import define, field
from exdrf_qt.models.fields import QtStringField
from PyQt5.QtCore import Qt

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf_dev.db.api import Tag  # noqa: F401

# exdrf-keep-start other_globals ----------------------------------------------

# exdrf-keep-end other_globals ------------------------------------------------


@define
class LabelField(QtStringField["Tag"]):
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

    # exdrf-keep-start other_label_attributes ---------------------------------

    # exdrf-keep-end other_label_attributes -----------------------------------

    def values(self, record: "Tag") -> Dict[Qt.ItemDataRole, Any]:
        return self.expand_value(
            (str("ID:") + str(record.id) + str(" Name:") + str(record.name)),
            EditRole=record.id,
        )

    # exdrf-keep-start extra_label_content ------------------------------------

    # exdrf-keep-end extra_label_content --------------------------------------


# exdrf-keep-start more_content ------------------------------------------------

# exdrf-keep-end more_content --------------------------------------------------
