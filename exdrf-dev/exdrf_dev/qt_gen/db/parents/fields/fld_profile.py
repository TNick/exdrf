# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/field.py.j2
# Don't change it manually.
from typing import TYPE_CHECKING

from attrs import define, field
from exdrf.constants import RecIdType
from exdrf_qt.models.fields import QtRefOneToOneField

if TYPE_CHECKING:
    from exdrf.resource import ExResource  # noqa: F401

    from exdrf_dev.db.api import Parent  # noqa: F401
    from exdrf_dev.db.api import Profile  # noqa: F401


@define
class ProfileField(QtRefOneToOneField["Parent"]):
    """ """

    name: str = field(default="profile", init=False)
    title: str = field(default="Profile")
    category: str = field(default="general")
    preferred_width: int = field(default=100)
    ref: "ExResource" = field(default=None, repr=False)

    def part_id(self, record: "Profile") -> RecIdType:
        """Compute the ID for one of the components of the field."""
        return record.id

    def part_label(self, record: "Profile") -> str:
        """Compute the label for one of the components of the field."""
        return str("ID:") + str(record.id) + str(" Bio:") + str(record.bio)
