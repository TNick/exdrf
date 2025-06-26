# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> c/m/field.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING

from attrs import define, field
from exdrf_qt.models.fields import QtBoolField

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf_dev.db.api import Parent  # noqa: F401

# exdrf-keep-start other_globals ----------------------------------------------

# exdrf-keep-end other_globals ------------------------------------------------


@define
class IsActiveField(QtBoolField["Parent"]):
    """Flag indicating if the parent is active."""

    name: str = field(default="is_active", init=False)
    title: str = field(default="Is Active")
    description: str = field(
        default=("Flag indicating if the parent is active.")
    )
    category: str = field(default="general")
    nullable: bool = field(default=False)
    preferred_width: int = field(default=100)
    true_str: str = field(default="Active")
    false_str: str = field(default="Inactive")

    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------

    # exdrf-keep-start extra_field_content ------------------------------------

    # exdrf-keep-end extra_field_content --------------------------------------


# exdrf-keep-start more_content -----------------------------------------------

# exdrf-keep-end more_content -------------------------------------------------
