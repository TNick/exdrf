# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/field.py.j2
# Don't change it manually.
from typing import TYPE_CHECKING

from attrs import define, field
from exdrf_qt.models.fields import QtFloatField

if TYPE_CHECKING:
    from exdrf_dev.db.api import CompositeKeyModel  # noqa: F401


@define
class SomeFloatField(QtFloatField["CompositeKeyModel"]):
    """A floating-point number.."""

    name: str = field(default="some_float", init=False)
    title: str = field(default="Some Float")
    description: str = field(default=("A floating-point number."))
    preferred_width: int = field(default=100)
    min: float = field(default=0.0)
    max: float = field(default=100.0)
    scale: int = field(default=2)
    unit: str = field(default="units")
    unit_symbol: str = field(default="u")
