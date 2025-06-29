from datetime import datetime
from typing import Optional

from attrs import define, field

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

# exdrf-keep-start other_globals ----------------------------------------------

# exdrf-keep-end other_globals ------------------------------------------------


@define
class Parent:
    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------
    children: Optional[list[str]] = field(default=None)
    created_at: Optional[datetime] = field(default=None)
    is_active: Optional[bool] = field(default=None)
    name: Optional[str] = field(default=None)
    profile: Optional[str] = field(default=None)
    tags: Optional[list[str]] = field(default=None)
    id: Optional[int] = field(default=None)

    # exdrf-keep-start extra_class_content -------------------------------------

    # exdrf-keep-end extra_class_content ---------------------------------------


# exdrf-keep-start more_content -----------------------------------------------

# exdrf-keep-end more_content -------------------------------------------------
