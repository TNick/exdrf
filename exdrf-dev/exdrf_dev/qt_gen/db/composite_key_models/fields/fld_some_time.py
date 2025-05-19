# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/field.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING

from attrs import define, field
from exdrf_qt.models.fields import QtTimeField

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf_dev.db.api import CompositeKeyModel  # noqa: F401


@define
class SomeTimeField(QtTimeField["CompositeKeyModel"]):
    """A time value."""

    name: str = field(default="some_time", init=False)
    title: str = field(default="Some Time")
    description: str = field(default=("A time value."))
    category: str = field(default="general")
    preferred_width: int = field(default=100)

    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------

    # exdrf-keep-start extra_field_content ------------------------------------

    # exdrf-keep-end extra_field_content --------------------------------------


# exdrf-keep-start more_content -----------------------------------------------

# exdrf-keep-end more_content -------------------------------------------------
