# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.
from typing import TYPE_CHECKING

from attrs import define, field
from exdrf_qt.models.fields import QtIntegerField

if TYPE_CHECKING:
    from exdrf_dev.db.models import RelatedItem  # noqa: F401


@define
class CompKeyPart2Field(QtIntegerField["RelatedItem"]):
    """Foreign key part 2 referencing CompositeKeyModel.."""

    name: str = field(default="comp_key_part2", init=False)
    title: str = field(default="Comp Key Part2")
    description: str = field(
        default=("Foreign key part 2 referencing CompositeKeyModel.")
    )
    visible: bool = field(default=True)
    nullable: bool = field(default=False)
    read_only: bool = field(default=False)
    resizable: bool = field(default=True)
    sortable: bool = field(default=True)
    filterable: bool = field(default=True)
    exportable: bool = field(default=True)
    qsearch: bool = field(default=True)
