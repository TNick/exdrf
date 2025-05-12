# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/field.py.j2
# Don't change it manually.
from typing import TYPE_CHECKING

from attrs import define, field
from exdrf_qt.models.fields import QtStringField

if TYPE_CHECKING:
    from exdrf_dev.db.api import Child  # noqa: F401


@define
class DataField(QtStringField["Child"]):
    """Some data associated with the child."""

    name: str = field(default="data", init=False)
    title: str = field(default="Data")
    description: str = field(default=("Some data associated with the child."))
    category: str = field(default="general")
    preferred_width: int = field(default=100)
    multiline: bool = field(default=True)
    min_length: int = field(default=1)
    max_length: int = field(default=200)
