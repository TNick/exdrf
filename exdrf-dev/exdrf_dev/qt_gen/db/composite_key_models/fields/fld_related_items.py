# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/field.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING

from attrs import define, field
from exdrf.constants import RecIdType
from exdrf_qt.models.fields import QtRefOneToManyField

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf.resource import ExResource  # noqa: F401

    from exdrf_dev.db.api import CompositeKeyModel  # noqa: F401
    from exdrf_dev.db.api import RelatedItem  # noqa: F401


@define
class RelatedItemsField(QtRefOneToManyField["CompositeKeyModel"]):
    """ """

    name: str = field(default="related_items", init=False)
    title: str = field(default="Related Items")
    category: str = field(default="general")
    preferred_width: int = field(default=100)
    show_n_labels: int = field(default=4)

    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------
    ref: "ExResource" = field(default=None, repr=False)

    def part_id(self, record: "RelatedItem") -> RecIdType:
        """Compute the ID for one of the components of the field."""
        return record.id

    def part_label(self, record: "RelatedItem") -> str:
        """Compute the label for one of the components of the field."""
        return str("ID:") + str(record.id)

    # exdrf-keep-start extra_field_content ------------------------------------

    # exdrf-keep-end extra_field_content --------------------------------------


# exdrf-keep-start more_content -----------------------------------------------

# exdrf-keep-end more_content -------------------------------------------------
