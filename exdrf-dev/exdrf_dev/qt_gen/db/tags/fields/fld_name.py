# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/field.py.j2
# Don't change it manually.
from typing import TYPE_CHECKING

from attrs import define, field
from exdrf_qt.models.fields import QtStringField

if TYPE_CHECKING:
    from exdrf_dev.db.api import Tag  # noqa: F401


@define
class NameField(QtStringField["Tag"]):
    """Unique name of the tag."""

    name: str = field(default="name", init=False)
    title: str = field(default="Name")
    description: str = field(default=("Unique name of the tag."))
    category: str = field(default="general")
    nullable: bool = field(default=False)
    preferred_width: int = field(default=100)
    max_length: int = field(default=50)
