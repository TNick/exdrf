from typing import TYPE_CHECKING

from attrs import define, field

from exdrf.constants import FIELD_TYPE_REF_MANY_TO_MANY
from exdrf.field_types.ref_base import RefBaseField

if TYPE_CHECKING:
    from exdrf.resource import ExResource  # noqa: F401


@define
class RefManyToManyField(RefBaseField):
    """This type of field is created by ManyToMany relations.

    In this type of relation there are many items of the present resource that
    are related to many items of the related resource. The relation is
    implemented by a third resource that contains the foreign keys to both
    resources and is referenced by the `ref_intermediate` attribute.

    It is asserted that in this case the `is_list` attribute is set to `True`.

    Attribute:
        ref_intermediate: The intermediate resource that implements the
            relation.
    """

    type_name: str = field(default=FIELD_TYPE_REF_MANY_TO_MANY)
    is_list: bool = field(default=True)

    ref_intermediate: "ExResource" = field(default=None, repr=False)

    def __repr__(self) -> str:
        return f"M2M({self.ref.name}, {self.ref_intermediate.name})"
