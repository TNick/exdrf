# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/field.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING

from attrs import define, field
from exdrf_qt.models.fields import QtStringField

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf_dev.db.api import RelatedItem  # noqa: F401


@define
class CompKeyPart1Field(QtStringField["RelatedItem"]):
    """Foreign key part 1 referencing CompositeKeyModel."""

    name: str = field(default="comp_key_part1", init=False)
    title: str = field(default="Comp Key Part1")
    description: str = field(
        default=("Foreign key part 1 referencing CompositeKeyModel.")
    )
    category: str = field(default="general")
    nullable: bool = field(default=False)
    preferred_width: int = field(default=100)
    max_length: int = field(default=50)

    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------

    # exdrf-keep-start extra_field_content ------------------------------------

    # exdrf-keep-end extra_field_content --------------------------------------


# exdrf-keep-start more_content -----------------------------------------------

# exdrf-keep-end more_content -------------------------------------------------
