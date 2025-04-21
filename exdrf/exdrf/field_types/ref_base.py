from typing import Optional

from attrs import define, field

from exdrf.field import ExField, FieldInfo
from exdrf.resource import ExResource

from exdrf.constants import RelType


@define
class RefBaseField(ExField):
    """Base class for resource relations.

    Attributes:
        ref: The related resource.
    """

    ref: "ExResource" = field(default=None, repr=False)


class RelExtraInfo(FieldInfo):
    """Parser for information about a related resource.

    Attributes:
        direction: The direction of the relationship. Can be "OneToMany",
            "ManyToOne", "OneToOne", or "ManyToMany".
    """

    direction: Optional[RelType] = None
