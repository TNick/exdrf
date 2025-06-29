from typing import Any

from attrs import define, field

from exdrf.constants import FIELD_TYPE_REF_ONE_TO_ONE
from exdrf.field_types.ref_base import RefBaseField


@define
class RefOneToOneField(RefBaseField):
    """This type of field is created by OneToOne relations.

    In this type of relation there is one item of the present resource
    that is related to one item of the related resource. The foreign key mey
    be in either the present, in the related resource but *not in both*.

    It is asserted that in this case the `is_list` attribute is set to
    `False`.
    """

    type_name: str = field(default=FIELD_TYPE_REF_ONE_TO_ONE)
    is_list: bool = field(default=False)
    subordinate: bool = field(default=False)

    def field_properties(self, explicit: bool = False) -> dict[str, Any]:
        result = super().field_properties(explicit)
        if self.subordinate or explicit:
            result["subordinate"] = self.subordinate
        return result

    def __repr__(self) -> str:
        return f"O2O({self.ref.name})"
