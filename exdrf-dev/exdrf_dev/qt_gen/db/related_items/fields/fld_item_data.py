# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/field.py.j2
# Don't change it manually.
from typing import TYPE_CHECKING

from attrs import define, field
from exdrf_qt.models.fields import QtStringField

if TYPE_CHECKING:
    from exdrf_dev.db.api import RelatedItem  # noqa: F401


@define
class ItemDataField(QtStringField["RelatedItem"]):
    """Data specific to the related item.."""

    name: str = field(default="item_data", init=False)
    title: str = field(default="Item Data")
    description: str = field(default=("Data specific to the related item."))
    category: str = field(default="general")
    preferred_width: int = field(default=100)
    max_length: int = field(default=200)
