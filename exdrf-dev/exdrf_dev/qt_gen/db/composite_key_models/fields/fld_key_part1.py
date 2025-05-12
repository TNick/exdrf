# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/field.py.j2
# Don't change it manually.
from typing import TYPE_CHECKING

from attrs import define, field
from exdrf_qt.models.fields import QtStringField

if TYPE_CHECKING:
    from exdrf_dev.db.api import CompositeKeyModel  # noqa: F401


@define
class KeyPart1Field(QtStringField["CompositeKeyModel"]):
    """First part of the composite primary key (string)."""

    name: str = field(default="key_part1", init=False)
    title: str = field(default="Key Part1")
    description: str = field(
        default=("First part of the composite primary key (string).")
    )
    category: str = field(default="keys")
    primary: bool = field(default=True)
    nullable: bool = field(default=False)
    preferred_width: int = field(default=100)
    max_length: int = field(default=50)
