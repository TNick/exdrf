# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/field.py.j2
# Don't change it manually.
from typing import TYPE_CHECKING

from attrs import define, field
from exdrf_qt.models.fields import QtIntegerField

if TYPE_CHECKING:
    from exdrf_dev.db.api import RelatedItem  # noqa: F401


@define
class IdField(QtIntegerField["RelatedItem"]):
    """Primary key for the related item."""

    name: str = field(default="id", init=False)
    title: str = field(default="Id")
    description: str = field(default=("Primary key for the related item."))
    category: str = field(default="keys")
    primary: bool = field(default=True)
    nullable: bool = field(default=False)
    preferred_width: int = field(default=100)
