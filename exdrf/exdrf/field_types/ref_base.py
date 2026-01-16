from typing import Any, Optional

from attrs import define, field

from exdrf.constants import RelType
from exdrf.field import ExField, FieldInfo
from exdrf.resource import ExResource


@define
class RefBaseField(ExField):
    """Base class for resource relations.

    Attributes:
        ref: The related resource.
        expect_lots: If true it indicates that the relation is expected to have
            many items. This is only valid when the parent side is 'many'
            (many-to-one or many-to-many relations from the parent's point of
            view).
    """

    ref: "ExResource" = field(default=None, repr=False)
    expect_lots: bool = field(default=False)

    def field_properties(self, explicit: bool = False) -> dict[str, Any]:
        result = super().field_properties(explicit)
        result["ref"] = self.ref.name
        return result


class RelExtraInfo(FieldInfo):
    """Parser for information about a related resource.

    Attributes:
        direction: The direction of the relationship. Can be "OneToMany",
            "ManyToOne", "OneToOne", or "ManyToMany".
        subordinate: If true it indicates that the child resource is parented
            into current resource through this relation. Child resources get
            deleted when the parent is deleted and they should not be
            independently managed at the top level. Instead, the widget for
            this relation in the parent resource will be adapted to show an
            editable list of children where the children are added and removed.
            This is only valid when the parent side is 'one' (one-to-many or
            one-to-one relations from the parent's point of view).
        expect_lots: If true it indicates that the relation is expected to have
            many items. This is only valid when the parent side is 'many'
            (many-to-one or many-to-many relations from the parent's point of
            view).
    """

    direction: Optional[RelType] = None
    subordinate: Optional[bool] = None
    expect_lots: Optional[bool] = False
