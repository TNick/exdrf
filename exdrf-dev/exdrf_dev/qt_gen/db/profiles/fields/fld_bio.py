# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/field.py.j2
# Don't change it manually.
from typing import TYPE_CHECKING

from attrs import define, field
from exdrf_qt.models.fields import QtStringField

if TYPE_CHECKING:
    from exdrf_dev.db.api import Profile  # noqa: F401


@define
class BioField(QtStringField["Profile"]):
    """Biography text for the profile."""

    name: str = field(default="bio", init=False)
    title: str = field(default="Bio")
    description: str = field(default=("Biography text for the profile."))
    category: str = field(default="general")
    preferred_width: int = field(default=100)
