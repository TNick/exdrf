from attrs import define, field

from exdrf.constants import FIELD_TYPE_REF_MANY_TO_ONE
from exdrf.field_types.ref_base import RefBaseField


@define
class RefManyToOneField(RefBaseField):
    """This type of field is created by ManyToOne relations.

    In this type of relation there are many items of the present
    resource that are related to one item of the related resource. Expect
    the foreign key to be in the *present* resource.

    It is asserted that in this case the `is_list` attribute is set to
    `False`.
    """

    type_name: str = field(default=FIELD_TYPE_REF_MANY_TO_ONE)
    is_list: bool = field(default=False)

    def __repr__(self) -> str:
        return f"M2O({self.ref.name})"
