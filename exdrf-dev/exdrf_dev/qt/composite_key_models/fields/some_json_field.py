# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.
from typing import TYPE_CHECKING

from attrs import define, field
from exdrf_qt.models.fields import QtFormattedField

if TYPE_CHECKING:
    from exdrf_dev.db.models import CompositeKeyModel  # noqa: F401


@define
class SomeJsonField(QtFormattedField["CompositeKeyModel"]):
    """A JSON object.."""

    name: str = field(default="some_json", init=False)
    title: str = field(default="Some Json")
    description: str = field(default=("A JSON object."))
    visible: bool = field(default=True)
    nullable: bool = field(default=True)
    read_only: bool = field(default=False)
    resizable: bool = field(default=True)
    sortable: bool = field(default=True)
    filterable: bool = field(default=True)
    exportable: bool = field(default=True)
    qsearch: bool = field(default=True)
