from datetime import date, time
from enum import StrEnum
from typing import Optional

from attrs import define, field

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

# exdrf-keep-start other_globals ----------------------------------------------

# exdrf-keep-end other_globals ------------------------------------------------


class SomeEnum(StrEnum):
    Pending = "PENDING"
    Processing = "PROCESSING"
    Completed = "COMPLETED"
    Failed = "FAILED"


@define(slots=True)
class CompositeKeyModel:
    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------
    description: Optional[str] = field(default=None)
    related_items: Optional[list[str]] = field(default=None)
    some_binary: Optional[bytes] = field(default=None)
    some_date: Optional[date] = field(default=None)
    some_enum: Optional[SomeEnum] = field(default=None)
    some_float: Optional[float] = field(default=None)
    some_json: Optional[str] = field(default=None)
    some_time: Optional[time] = field(default=None)
    key_part1: Optional[str] = field(default=None)
    key_part2: Optional[int] = field(default=None)

    # exdrf-keep-start extra_class_content -------------------------------------

    # exdrf-keep-end extra_class_content ---------------------------------------


# exdrf-keep-start more_content -----------------------------------------------

# exdrf-keep-end more_content -------------------------------------------------
