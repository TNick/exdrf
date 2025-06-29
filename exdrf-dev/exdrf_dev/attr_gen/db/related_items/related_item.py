from typing import Optional

from attrs import define, field

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

# exdrf-keep-start other_globals ----------------------------------------------

# exdrf-keep-end other_globals ------------------------------------------------


@define
class RelatedItem:
    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------
    comp_key_owner: Optional[str] = field(default=None)
    comp_key_part1: Optional[str] = field(default=None)
    comp_key_part2: Optional[int] = field(default=None)
    item_data: Optional[str] = field(default=None)
    some_int: Optional[int] = field(default=None)
    id: Optional[int] = field(default=None)

    # exdrf-keep-start extra_class_content -------------------------------------

    # exdrf-keep-end extra_class_content ---------------------------------------


# exdrf-keep-start more_content -----------------------------------------------

# exdrf-keep-end more_content -------------------------------------------------
