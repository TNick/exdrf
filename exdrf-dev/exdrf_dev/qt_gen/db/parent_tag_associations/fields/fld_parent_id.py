# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> c/m/field.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING

from attrs import define, field
from exdrf_qt.models.fields import QtIntegerField

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf_dev.db.api import ParentTagAssociation  # noqa: F401

# exdrf-keep-start other_globals ----------------------------------------------

# exdrf-keep-end other_globals ------------------------------------------------


@define
class ParentIdField(QtIntegerField["ParentTagAssociation"]):
    """Foreign key to the parents table."""

    name: str = field(default="parent_id", init=False)
    title: str = field(default="Parent Id")
    description: str = field(default=("Foreign key to the parents table."))
    category: str = field(default="keys")
    primary: bool = field(default=True)
    nullable: bool = field(default=False)
    preferred_width: int = field(default=100)

    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------

    # exdrf-keep-start extra_field_content ------------------------------------

    # exdrf-keep-end extra_field_content --------------------------------------


# exdrf-keep-start more_content -----------------------------------------------

# exdrf-keep-end more_content -------------------------------------------------
