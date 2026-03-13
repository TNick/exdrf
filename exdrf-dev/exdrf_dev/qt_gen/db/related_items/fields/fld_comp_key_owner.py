# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> c/m/field.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING, Any, List, Optional, Type

from attrs import define, field
from exdrf.constants import RecIdType
from exdrf_qt.models.fi_op import filter_op_registry
from exdrf_qt.models.fields import QtRefManyToOneField

from exdrf_dev.qt_gen.db.composite_key_models.widgets.composite_key_model_selector import (
    QtCompositeKeyModelMuSe,
    QtCompositeKeyModelSiSe,
)

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf.filter import FieldFilter
    from exdrf.resource import ExResource  # noqa: F401
    from exdrf_qt.field_ed.api import DrfSelMultiEditor, DrfSelOneEditor
    from exdrf_qt.models.selector import Selector

    from exdrf_dev.db.api import CompositeKeyModel  # noqa: F401
    from exdrf_dev.db.api import RelatedItem  # noqa: F401

# exdrf-keep-start other_globals ----------------------------------------------

# exdrf-keep-end other_globals ------------------------------------------------


@define
class CompKeyOwnerField(QtRefManyToOneField["RelatedItem"]):
    """ """

    name: str = field(default="comp_key_owner", init=False)
    title: str = field(default="Comp Key Owner")
    category: str = field(default="general")
    preferred_width: int = field(default=100)
    provides: List[str] = field(factory=lambda: [])
    depends_on: List[str] = field(factory=lambda: [])

    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------

    ref: "ExResource" = field(default=None, repr=False)
    selector_one_class: Optional[Type["DrfSelOneEditor"]] = field(
        default=QtCompositeKeyModelSiSe,
        repr=False,
    )
    selector_multi_class: Optional[Type["DrfSelMultiEditor"]] = field(
        default=QtCompositeKeyModelMuSe,
        repr=False,
    )

    def part_id(self, record: "CompositeKeyModel") -> RecIdType:
        """Compute the ID for one of the components of the field."""
        return (
            record.key_part1,
            record.key_part2,
        )

    def part_label(self, record: "CompositeKeyModel") -> str:
        """Compute the label for one of the components of the field."""
        from .db.composite_key_model import composite_key_model_label

        return composite_key_model_label(record, self.ctx)

    def apply_filter(
        self,
        item: "FieldFilter",
        selector: "Selector",
        no_dia: Optional[str] = None,
    ) -> Any:
        from exdrf_dev.db.api import CompositeKeyModel as DbCompositeKeyModel

        predicate = filter_op_registry[item.op].predicate
        related_entity = getattr(self.resource.db_model, self.name)
        subq = related_entity.has(
            predicate(DbCompositeKeyModel.description, item.vl),
        )
        return subq

    # Comparator/merge hooks: override cmp_extract_value, cmp_normalize_value,
    # cmp_available_methods, cmp_create_manual_editor, cmp_apply_resolved_value
    # as needed (defaults from QtField).
    # exdrf-keep-start cmp_methods -------------------------------------------

    # exdrf-keep-end cmp_methods ----------------------------------------------

    # exdrf-keep-start extra_field_content ------------------------------------

    # exdrf-keep-end extra_field_content --------------------------------------


# exdrf-keep-start more_content -----------------------------------------------

# exdrf-keep-end more_content -------------------------------------------------
