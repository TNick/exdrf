# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.
from typing import TYPE_CHECKING

from attrs import define, field
from exdrf_qt.models.fields import QtStringField

if TYPE_CHECKING:
    from exdrf_dev.db.models import CompositeKeyModel  # noqa: F401


@define
class KeyPart1Field(QtStringField["CompositeKeyModel"]):
    """First part of the composite primary key (string).."""

    name: str = field(default="key_part1", init=False)
    title: str = field(default="Key Part1")
    description: str = field(
        default=("First part of the composite primary key (string).")
    )
    primary: bool = field(default=True)
    visible: bool = field(default=True)
    nullable: bool = field(default=False)
    read_only: bool = field(default=False)
    resizable: bool = field(default=True)
    sortable: bool = field(default=True)
    filterable: bool = field(default=True)
    exportable: bool = field(default=True)
    qsearch: bool = field(default=True)

    multiline: bool = field(default=False)
    max_length: int = field(default=50)
