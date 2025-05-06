# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.
from typing import TYPE_CHECKING

from attrs import define, field
from exdrf_qt.models.fields import QtIntegerField

if TYPE_CHECKING:
    from exdrf_dev.db.models import RelatedItem  # noqa: F401


@define
class SomeIntField(QtIntegerField["RelatedItem"]):
    """An integer value associated with the related item.."""

    name: str = field(default="some_int", init=False)
    title: str = field(default="Some Int")
    description: str = field(
        default=("An integer value associated with the related item.")
    )
    visible: bool = field(default=True)
    nullable: bool = field(default=True)
    read_only: bool = field(default=False)
    resizable: bool = field(default=True)
    sortable: bool = field(default=True)
    filterable: bool = field(default=True)
    exportable: bool = field(default=True)
    qsearch: bool = field(default=True)

    min: int = field(default=0)
    max: int = field(default=1000)
