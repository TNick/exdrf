from functools import partial
from typing import TYPE_CHECKING, Dict

from attrs import define, field

if TYPE_CHECKING:
    from exdrf_qt.controls.constraints.concept_base import Concept
    from exdrf_qt.field_ed.base import DrfFieldEd


@define(slots=True, kw_only=True, frozen=True)
class Constraints:
    """Groups a set of constraints and offers a centralized mechanism for
    reacting to changes in the editor.

    A single instance can be used in a single editor or across multiple editors.

    The class contain concepts that have unique keys. Field editors can register
    themselves as editors for a certain concept. All field editors
    that register themselves for a concept will share the same value,
    and changing one will change the value for all. Moreover, when used
    across multiple editors, this offers the ability to disable the
    field editors in subsequent editors so that consistency is maintained
    and the user sets the value only one time, at the top level.

    The field editors can also subscribe to changes, so that the values
    available to the user are filtered to only include the values that are
    valid for the concept.
    """

    concepts: Dict[str, "Concept"] = field(factory=dict, repr=False)

    def get_concept(self, name: str) -> "Concept":
        from exdrf_qt.controls.constraints.concept_base import Concept

        found = self.concepts.get(name)
        if not found:
            found = Concept(uniq=name)
            self.concepts[name] = found

        return found

    def register_provider(self, concept: str, provider: "DrfFieldEd") -> None:
        """Register a provider for a concept."""
        found = self.get_concept(concept)

        found.providers.append(provider)
        provider.controlChanged.connect(  # type: ignore
            partial(self.ping_subscribers, found.uniq, provider)
        )
        if len(found.providers) == 1:
            self.ping_subscribers(found.uniq, provider)

    def register_subscriber(
        self, concept: str, subscriber: "DrfFieldEd"
    ) -> None:
        """Register a subscriber for a concept."""
        found = self.get_concept(concept)
        found.subscribers.append(subscriber)

    def ping_subscribers(
        self, concept_key: str, except_provider: "DrfFieldEd"
    ) -> None:
        """Ping all subscribers for a concept."""

        if self.concepts[concept_key].updating:
            return
        try:
            self.concepts[concept_key].updating = True
            new_value = except_provider.field_value

            # Inform siblings that the value has changed.
            for provider in self.concepts[concept_key].providers:
                if provider is not except_provider:
                    provider.change_field_value(new_value)
            # Inform subscribers that the value has changed.
            for subscriber in self.concepts[concept_key].subscribers:
                subscriber.constraints_changed(concept_key, new_value)
        finally:
            self.concepts[concept_key].updating = False
