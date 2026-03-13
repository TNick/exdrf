# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> c/m/field.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING, List, Optional, Tuple

from attrs import define, field
from exdrf_qt.models.fields import QtIntegerField

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf_dev.db.api import Profile  # noqa: F401

# exdrf-keep-start other_globals ----------------------------------------------

# exdrf-keep-end other_globals ------------------------------------------------


@define
class ParentIdField(QtIntegerField["Profile"]):
    """Foreign key linking to the parent (must be unique)."""

    name: str = field(default="parent_id", init=False)
    title: str = field(default="Parent Id")
    description: str = field(
        default=("Foreign key linking to the parent (must be unique).")
    )
    fk_to: Optional[str] = field(default="parent", repr=False)
    category: str = field(default="general")
    nullable: bool = field(default=False)
    preferred_width: int = field(default=100)
    enum_values: List[Tuple[int, str]] = field(factory=lambda: [])

    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------

    # Comparator/merge hooks: override cmp_extract_value, cmp_normalize_value,
    # cmp_available_methods, cmp_create_manual_editor, cmp_apply_resolved_value
    # as needed (defaults from QtField).
    # exdrf-keep-start cmp_methods -------------------------------------------

    # exdrf-keep-end cmp_methods ----------------------------------------------

    # exdrf-keep-start extra_field_content ------------------------------------

    # exdrf-keep-end extra_field_content --------------------------------------


# exdrf-keep-start more_content -----------------------------------------------

# exdrf-keep-end more_content -------------------------------------------------
