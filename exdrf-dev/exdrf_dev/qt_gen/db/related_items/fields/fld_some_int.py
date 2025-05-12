# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/field.py.j2
# Don't change it manually.
from typing import TYPE_CHECKING

from attrs import define, field
from exdrf_qt.models.fields import QtIntegerField

if TYPE_CHECKING:
    from exdrf_dev.db.api import RelatedItem  # noqa: F401


@define
class SomeIntField(QtIntegerField["RelatedItem"]):
    """An integer value associated with the related item."""

    name: str = field(default="some_int", init=False)
    title: str = field(default="Some Int")
    description: str = field(
        default=("An integer value associated with the related item.")
    )
    category: str = field(default="general")
    preferred_width: int = field(default=100)
    min: int = field(default=0)
    max: int = field(default=1000)
    unit: str = field(default="units")
    unit_symbol: str = field(default="u")
