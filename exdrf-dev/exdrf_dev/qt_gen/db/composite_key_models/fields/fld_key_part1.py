# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> c/m/field.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING, List, Tuple

from attrs import define, field
from exdrf_qt.models.fields import QtStringField

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf_dev.db.api import CompositeKeyModel  # noqa: F401

# exdrf-keep-start other_globals ----------------------------------------------

# exdrf-keep-end other_globals ------------------------------------------------


@define
class KeyPart1Field(QtStringField["CompositeKeyModel"]):
    """First part of the composite primary key (string)."""

    name: str = field(default="key_part1", init=False)
    title: str = field(default="Key Part1")
    description: str = field(
        default=("First part of the composite primary key (string).")
    )
    category: str = field(default="keys")
    nullable: bool = field(default=False)
    primary: bool = field(default=True)
    preferred_width: int = field(default=100)
    max_length: int = field(default=50)
    enum_values: List[Tuple[str, str]] = field(factory=lambda: [])

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
