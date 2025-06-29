from typing import Any

from attrs import define, field

from exdrf.constants import FIELD_TYPE_REF_ONE_TO_MANY
from exdrf.field_types.ref_base import RefBaseField


@define
class RefOneToManyField(RefBaseField):
    """This type of field is created by OneToMany relations.

    In this type of relation there is one item of the present resource
    that is related to many items of the related resource. Expect the foreign
    key to be in the *related* resource.

    It is asserted that in this case the `is_list` attribute is set to
    `True`.
    """

    type_name: str = field(default=FIELD_TYPE_REF_ONE_TO_MANY)
    is_list: bool = field(default=True)
    subordinate: bool = field(default=False)

    def field_properties(self, explicit: bool = False) -> dict[str, Any]:
        result = super().field_properties(explicit)
        if self.subordinate or explicit:
            result["subordinate"] = self.subordinate
        return result

    def __repr__(self) -> str:
        return f"O2M({self.ref.name})"
