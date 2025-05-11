# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/field.py.j2
# Don't change it manually.
from typing import TYPE_CHECKING, List

from attrs import define, field
from exdrf_qt.models.fields import QtEnumField

if TYPE_CHECKING:
    from exdrf_dev.db.api import CompositeKeyModel  # noqa: F401


@define
class SomeEnumField(QtEnumField["CompositeKeyModel"]):
    """An enum value representing status.."""

    name: str = field(default="some_enum", init=False)
    title: str = field(default="Some Enum")
    description: str = field(default=("An enum value representing status."))
    category: str = field(default="general")
    preferred_width: int = field(default=100)
    enum_values: List[str] = field(
        factory=lambda: ["PENDING", "PROCESSING", "COMPLETED", "FAILED"]
    )
