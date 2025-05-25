# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> c/m/field.py.j2
# Don't change it manually.

from datetime import date
from typing import TYPE_CHECKING

from attrs import define, field
from exdrf_qt.models.fields import QtDateField

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf_dev.db.api import CompositeKeyModel  # noqa: F401


@define
class SomeDateField(QtDateField["CompositeKeyModel"]):
    """A date value."""

    name: str = field(default="some_date", init=False)
    title: str = field(default="Some Date")
    description: str = field(default=("A date value."))
    category: str = field(default="general")
    preferred_width: int = field(default=100)
    min: date = field(default=date(2020, 1, 1))
    max: date = field(default=date(2030, 12, 31))

    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------

    # exdrf-keep-start extra_field_content ------------------------------------

    # exdrf-keep-end extra_field_content --------------------------------------


# exdrf-keep-start more_content -----------------------------------------------

# exdrf-keep-end more_content -------------------------------------------------
