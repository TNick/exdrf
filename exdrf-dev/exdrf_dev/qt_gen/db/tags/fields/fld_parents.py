# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> c/m/field.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING, Any

from attrs import define, field
from exdrf.constants import RecIdType
from exdrf_qt.models.fi_op import filter_op_registry
from exdrf_qt.models.fields import QtRefManyToManyField
from sqlalchemy.orm import aliased

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf.filter import FieldFilter
    from exdrf.resource import ExResource  # noqa: F401
    from exdrf_qt.models.selector import Selector

    from exdrf_dev.db.api import Parent  # noqa: F401
    from exdrf_dev.db.api import Tag  # noqa: F401


@define
class ParentsField(QtRefManyToManyField["Tag"]):
    """ """

    name: str = field(default="parents", init=False)
    title: str = field(default="Parents")
    category: str = field(default="general")
    preferred_width: int = field(default=100)
    show_n_labels: int = field(default=4)

    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------

    ref: "ExResource" = field(default=None, repr=False)

    def part_id(self, record: "Parent") -> RecIdType:
        """Compute the ID for one of the components of the field."""
        return record.id

    def part_label(self, record: "Parent") -> str:
        """Compute the label for one of the components of the field."""
        return str("ID:") + str(record.id) + str(" Name:") + str(record.name)

    def apply_filter(self, item: "FieldFilter", selector: "Selector") -> Any:
        from exdrf_dev.db.api import Parent as DbParent

        predicate = filter_op_registry[item.op].predicate
        related_entity = getattr(self.resource.db_model, self.name)
        # M2M(Parent, ParentTagAssociation)
        subq = related_entity.any(
            predicate(DbParent.name, item.vl),
        )
        return subq

        with_alias = aliased(DbParent)
        predicate = filter_op_registry[item.op].predicate
        selector.joins.append(
            (
                with_alias,
                getattr(self.resource.db_model, self.name),
                {"isouter": True},
            )
        )

        return predicate(
            with_alias.name,
            item.vl,
        )

    # exdrf-keep-start extra_field_content ------------------------------------

    # exdrf-keep-end extra_field_content --------------------------------------


# exdrf-keep-start more_content -----------------------------------------------

# exdrf-keep-end more_content -------------------------------------------------
