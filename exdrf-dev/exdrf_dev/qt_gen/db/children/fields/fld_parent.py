# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/field.py.j2
# Don't change it manually.
from typing import TYPE_CHECKING

from attrs import define, field
from exdrf.constants import RecIdType
from exdrf_qt.models.fields import QtRefManyToOneField

if TYPE_CHECKING:
    from exdrf.resource import ExResource  # noqa: F401

    from exdrf_dev.db.api import Child  # noqa: F401
    from exdrf_dev.db.api import Parent  # noqa: F401


@define
class ParentField(QtRefManyToOneField["Child"]):
    """ """

    name: str = field(default="parent", init=False)
    title: str = field(default="Parent")
    preferred_width: int = field(default=100)
    ref: "ExResource" = field(default=None, repr=False)

    def part_id(self, record: "Parent") -> RecIdType:
        """Compute the ID for one of the components of the field."""
        return record.id

    def part_label(self, record: "Parent") -> str:
        """Compute the label for one of the components of the field."""
        return str("ID:") + str(record.id) + str(" Name:") + str(record.name)
