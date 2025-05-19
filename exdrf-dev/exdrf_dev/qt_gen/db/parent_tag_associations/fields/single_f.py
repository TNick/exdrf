# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/single_f.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING, Any, Dict

from attrs import define, field
from exdrf_qt.models.fields import QtStringField
from PyQt5.QtCore import Qt

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf_dev.db.api import ParentTagAssociation  # noqa: F401


@define
class LabelField(QtStringField["ParentTagAssociation"]):
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

    def values(
        self, record: "ParentTagAssociation"
    ) -> Dict[Qt.ItemDataRole, Any]:
        return self.expand_value(
            (
                str("Parent:")
                + str(record.parent_id)
                + str(" Tag:")
                + str(record.tag_id)
            ),
            EditRole=(
                record.parent_id,
                record.tag_id,
            ),
        )

    # exdrf-keep-start extra_label_content ------------------------------------

    # exdrf-keep-end extra_label_content --------------------------------------


# exdrf-keep-start more_content ------------------------------------------------

# exdrf-keep-end more_content --------------------------------------------------
