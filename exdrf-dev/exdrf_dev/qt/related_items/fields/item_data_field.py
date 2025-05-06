# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.
from typing import TYPE_CHECKING

from attrs import define, field
from exdrf_qt.models.fields import QtStringField

if TYPE_CHECKING:
    from exdrf_dev.db.models import RelatedItem  # noqa: F401


@define
class ItemDataField(QtStringField["RelatedItem"]):
    """Data specific to the related item.."""

    name: str = field(default="item_data", init=False)
    title: str = field(default="Item Data")
    description: str = field(default=("Data specific to the related item."))
    visible: bool = field(default=True)
    nullable: bool = field(default=True)
    read_only: bool = field(default=False)
    resizable: bool = field(default=True)
    sortable: bool = field(default=True)
    filterable: bool = field(default=True)
    exportable: bool = field(default=True)
    qsearch: bool = field(default=True)

    multiline: bool = field(default=False)
    max_length: int = field(default=200)
