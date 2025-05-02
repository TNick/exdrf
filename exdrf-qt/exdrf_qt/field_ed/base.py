from typing import TYPE_CHECKING, Any, Optional

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.validator import ValidationResult

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext


class DrfFieldEd(QtUseContext):
    """Base class for field editor widgets.

    Attributes:
        field_value: The value of the field.
        nullable: Indicates if the field can be null.
        description: A description of the field shown as tooltip and
            in the status bar.

    Signals:
        controlChanged: Signal emitted when the value in the control changes.
            It will only be emitted for valid values for that field.
        enteredErrorState: Signal emitted when the field enters an error state.
            The value is the error message.
    """

    field_value: Any
    nullable: bool = False
    description: Optional[str] = ""

    controlChanged = pyqtSignal()
    enteredErrorState = pyqtSignal(str)

    def __init__(
        self: QWidget,  # type: ignore[override]
        ctx: "QtContext",
        description: Optional[str] = None,
        nullable: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.ctx = ctx
        self.field_value = None
        self.description = description or ""
        self.nullable = nullable

        self.apply_description()

    def apply_description(self: QWidget):  # type: ignore[override]
        """Apply the description to the widget."""
        if self.description:
            self.setToolTip(self.description)
            self.setStatusTip(self.description)

    def change_field_value(self, new_value: Any) -> None:
        """Change the field value."""
        raise NotImplementedError(
            "change_field_value() must be implemented in subclasses."
        )

    def is_valid(self) -> ValidationResult:
        """Check if the field value is valid.

        By default we check for NULL when the field is not nullable.
        """
        if self.field_value is not None:
            return ValidationResult(
                value=self.field_value,
            )
        return ValidationResult(
            reason="NULL",
            error=self.null_error(),
        )

    def null_error(self):
        """Create the error message for NULL when the field is not nullable."""
        return self.t("cmn.err.field_is_empty", "Field cannot be empty")
