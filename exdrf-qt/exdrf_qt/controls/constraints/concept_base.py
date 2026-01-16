from typing import TYPE_CHECKING, List

from attrs import define, field

if TYPE_CHECKING:
    from exdrf_qt.field_ed.base import DrfFieldEd


@define(slots=True, kw_only=True)
class Concept:
    """A concept represents a field which can provide a value and
    can be used across multiple editors.

    Attributes:
        uniq: The unique identifier of the concept.
        providers: The list of providers for the concept.
        subscribers: The list of subscribers for the concept.
        updating: Indicates if the concept is currently being updated.
            The Constraints will ensure that the subscribers are not pinged
            twice for the same change.
    """

    uniq: str
    providers: List["DrfFieldEd"] = field(factory=list, repr=False)
    subscribers: List["DrfFieldEd"] = field(factory=list, repr=False)
    updating: bool = False
