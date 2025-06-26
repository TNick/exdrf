# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> c/m/field.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING

from attrs import define, field
from exdrf_qt.models.fields import QtIntegerField

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf_dev.db.api import RelatedItem  # noqa: F401

# exdrf-keep-start other_globals ----------------------------------------------

# exdrf-keep-end other_globals ------------------------------------------------


@define
class SomeIntField(QtIntegerField["RelatedItem"]):
    """An integer value associated with the related item."""

    name: str = field(default="some_int", init=False)
    title: str = field(default="Some Int")
    description: str = field(
        default=("An integer value associated with the related item.")
    )
    category: str = field(default="general")
    preferred_width: int = field(default=100)
    min: int = field(default=0)
    max: int = field(default=1000)
    unit: str = field(default="units")
    unit_symbol: str = field(default="u")

    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------

    # exdrf-keep-start extra_field_content ------------------------------------

    # exdrf-keep-end extra_field_content --------------------------------------


# exdrf-keep-start more_content -----------------------------------------------

# exdrf-keep-end more_content -------------------------------------------------
