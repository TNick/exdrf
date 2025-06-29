from typing import Optional

from attrs import define, field

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

# exdrf-keep-start other_globals ----------------------------------------------

# exdrf-keep-end other_globals ------------------------------------------------


@define
class ParentTagAssociation:
    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------
    parent_id: Optional[int] = field(default=None)
    tag_id: Optional[int] = field(default=None)

    # exdrf-keep-start extra_class_content -------------------------------------

    # exdrf-keep-end extra_class_content ---------------------------------------


# exdrf-keep-start more_content -----------------------------------------------

# exdrf-keep-end more_content -------------------------------------------------
