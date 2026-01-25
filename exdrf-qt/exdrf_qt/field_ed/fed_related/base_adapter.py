from typing import TYPE_CHECKING, Any, Sequence, Tuple

from attrs import define, field
from exdrf.validator import ValidationResult

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext
    from exdrf_qt.field_ed.fed_related.fed_related import DrfRelated
    from exdrf_qt.models.model import QtModel
    from exdrf_qt.models.record import QtRecord


@define
class BaseAdapter:
    """Base class for the related editor adapters."""

    ctx: "QtContext" = field(repr=False)
    core: "DrfRelated" = field(repr=False)

    def started(self) -> None:
        """The adapter has been started."""

    def add_records(self, records: Sequence["QtRecord"]) -> None:
        """The user wants to add some records from the source list.

        Args:
            records: The records to add. Guaranteed to be loaded, without error,
                and with a non-none database ID.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    def remove_records(self, records: Sequence[Tuple["QtRecord", int]]) -> None:
        """The user wants to remove some records from the destination list.

        Args:
            records: The records to remove.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    def change_field_value(self, new_value) -> None:
        """The field value has changed. We need to clear and load.

        Args:
            new_value: The new field value.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    def load_value_from(self, record: Any):
        raise NotImplementedError("Subclasses must implement this method.")

    def save_value_to(self, record: Any):
        raise NotImplementedError("Subclasses must implement this method.")

    def validate_control(self) -> "ValidationResult":
        return ValidationResult(value=self.core._field_value or [])

    def adjust_model(self, model: "QtModel") -> None:
        """Adjust the model to the adapter.

        Args:
            model: The model to adjust.
        """
