from typing import Any, List, Optional, Tuple

from attrs import define, field
from pydantic import Field, field_validator

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
        provides: indicates the concept that this field provides. This is
            usually set at the resource level but can be overridden at the field
            level.
        depends_on: indicates the concepts that this field depends on. This is
            usually set at the resource level but can be overridden at the field
            level.
    """

    ref: "ExResource" = field(default=None, repr=False)
    expect_lots: bool = field(default=False)
    provides: List[str] = field(factory=list)
    depends_on: List[str] = field(factory=list)

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
        provides: indicates the concept that this field provides. This is
            usually set at the resource level but can be overridden at the field
            level.
        depends_on: indicates the concepts that this field depends on. This is
            usually set at the resource level but can be overridden at the field
            level.
        bridge: Even if the relation type is declared as OneToMany, the
            other side is a junction table with extra attributes. The value is
            the name of the resource on the other side.
    """

    direction: Optional[RelType] = None
    subordinate: Optional[bool] = None
    expect_lots: Optional[bool] = False
    provides: List[str] = Field(default_factory=list)
    depends_on: List[Tuple[str, str]] = Field(default_factory=list)
    bridge: Optional[str] = None

    @field_validator("provides", mode="before")
    @classmethod
    def parse_provides(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @field_validator("depends_on", mode="before")
    @classmethod
    def parse_depends_on(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            result = []
            for part in v.split(","):
                if not part.strip():
                    continue
                concept, target = part.strip().split(":", maxsplit=1)
                result.append((concept.strip(), target.strip()))
            return result
        return v
