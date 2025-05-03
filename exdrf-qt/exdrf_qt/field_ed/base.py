from typing import TYPE_CHECKING, Any, Optional

from PyQt5.QtCore import pyqtProperty, pyqtSignal  # type: ignore
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

    Qt Properties:
        clearable: Indicates if the field is nullable.
    """

    field_value: Any
    _nullable: bool = False
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

    @property
    def nullable(self) -> bool:
        """Get the nullable property."""
        return self._nullable

    @nullable.setter
    def nullable(self, value: bool) -> None:
        """Set the nullable property."""
        self._nullable = value
        if hasattr(self, "ac_clear") and self.ac_clear is not None:
            # We have an action to clear the field...
            if value:
                # ... and so we should.
                self.ac_clear.setEnabled(self.field_value is not None)
            else:
                # ... but we should not.
                self.ac_clear.deleteLater()
                self.ac_clear = None
        else:
            # We don't have an action to clear the field...
            if value:
                # ... but we should have one.
                self.add_clear_to_null_action()
            else:
                # ... and we should not so all is well in the world.
                pass

    def add_clear_to_null_action(self) -> None:
        pass

    def getClearable(self) -> bool:
        """Tell if the field is nullable.

        This is a support function for implementing the clearable property.
        """
        return self.nullable

    def setClearable(self, clearable: bool) -> None:
        """Set the nullable property and update the editor accordingly.

        Because of the way Qt implements properties, the subclass method will
        not be called. To work around this, reimplement set_nullable_hooks
        instead.
        """
        self.nullable = clearable

    clearable = pyqtProperty(bool, fget=getClearable, fset=setClearable)
