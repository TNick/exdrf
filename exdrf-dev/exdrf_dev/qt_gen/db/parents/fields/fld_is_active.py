# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/field.py.j2
# Don't change it manually.
from typing import TYPE_CHECKING

from attrs import define, field
from exdrf_qt.models.fields import QtBoolField

if TYPE_CHECKING:
    from exdrf_dev.db.api import Parent  # noqa: F401


@define
class IsActiveField(QtBoolField["Parent"]):
    """Flag indicating if the parent is active.."""

    name: str = field(default="is_active", init=False)
    title: str = field(default="Is Active")
    description: str = field(
        default=("Flag indicating if the parent is active.")
    )
    nullable: bool = field(default=False)
    preferred_width: int = field(default=100)
    true_str: str = field(default="Active")
    false_str: str = field(default="Inactive")
