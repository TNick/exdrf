# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> c/m/field.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING, Any

from attrs import define, field
from exdrf.constants import RecIdType
from exdrf_qt.models.fi_op import filter_op_registry
from exdrf_qt.models.fields import QtRefOneToManyField
from sqlalchemy.orm import aliased

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf.filter import FieldFilter
    from exdrf.resource import ExResource  # noqa: F401
    from exdrf_qt.models.selector import Selector

    from exdrf_dev.db.api import Child  # noqa: F401
    from exdrf_dev.db.api import Parent  # noqa: F401

# exdrf-keep-start other_globals ----------------------------------------------

# exdrf-keep-end other_globals ------------------------------------------------


@define
class ChildrenField(QtRefOneToManyField["Parent"]):
    """ """

    name: str = field(default="children", init=False)
    title: str = field(default="Children")
    category: str = field(default="general")
    preferred_width: int = field(default=100)
    subordinate: bool = field(default=False)
    show_n_labels: int = field(default=4)

    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------

    ref: "ExResource" = field(default=None, repr=False)

    def part_id(self, record: "Child") -> RecIdType:
        """Compute the ID for one of the components of the field."""
        return record.id

    def part_label(self, record: "Child") -> str:
        """Compute the label for one of the components of the field."""
        return (
            str("ID:")
            + str(record.id)
            + str(" Parent ")
            + str(record.parent.name)
            + str(" Data:")
            + str(record.data)
        )

    def apply_filter(self, item: "FieldFilter", selector: "Selector") -> Any:
        from exdrf_dev.db.api import Child as DbChild

        predicate = filter_op_registry[item.op].predicate
        related_entity = getattr(self.resource.db_model, self.name)
        # O2M(Child)
        subq = related_entity.any(
            predicate(DbChild.data, item.vl),
        )
        return subq

        with_alias = aliased(DbChild)
        predicate = filter_op_registry[item.op].predicate
        selector.joins.append(
            (
                with_alias,
                getattr(self.resource.db_model, self.name),
                {"isouter": True},
            )
        )

        return predicate(
            with_alias.data,
            item.vl,
        )

    # exdrf-keep-start extra_field_content ------------------------------------

    # exdrf-keep-end extra_field_content --------------------------------------


# exdrf-keep-start more_content -----------------------------------------------

# exdrf-keep-end more_content -------------------------------------------------
