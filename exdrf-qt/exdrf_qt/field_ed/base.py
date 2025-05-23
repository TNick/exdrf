from typing import TYPE_CHECKING, Any, Optional

from exdrf.validator import ValidationResult
from PyQt5.QtCore import pyqtProperty, pyqtSignal  # type: ignore
from PyQt5.QtWidgets import QWidget

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext


class DrfFieldEd(QtUseContext):
    """Base class for field editor widgets.

    Attributes:
        name: the member of the database model that this field editor is for.
            This is used by the `save_value_to_db()` method to save the current
            value to the database. `EditorDb` uses that method to provide a
            default way of transferring the data from the editor to the
            database model.
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
        name: The name of the field in the database record.
    """

    _name: str
    _field_value: Any
    _nullable: bool = False
    _read_only: bool = False
    description: Optional[str]

    controlChanged = pyqtSignal()
    enteredErrorState = pyqtSignal(str)

    def __init__(  # type: ignore
        self: QWidget,  # type: ignore
        ctx: "QtContext",
        name: Optional[str] = None,
        description: Optional[str] = None,
        nullable: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)  # type: ignore
        self.ctx = ctx
        self._field_value = None
        self.description = description or ""
        self._name = name or ""
        self.nullable = nullable

        self.apply_description()

    @property
    def field_value(self) -> Any:
        """Get the field value."""
        return self._field_value

    @field_value.setter
    def field_value(self, value: Any) -> None:
        """Set the field value."""
        self._change_field_value(value)

    def _change_field_value(self, value: Any) -> None:
        """Set the field value."""
        if self._field_value != value:
            # Change the value and signal the change.
            self._field_value = value
            self.controlChanged.emit()  # type: ignore

    def save_value_to_db(self, db_item: Any):
        """Save the field value into the database record.

        Attributes:
            db_item: The database item to save the field value to.
        """
        if not self._name:
            raise ValueError("Field name is not set.")
        setattr(db_item, self._name, self.field_value)

    def load_value_from_db(self, db_item: Any):
        """Load the field value from the database record.

        Attributes:
            db_item: The database item to load the field value from.
        """
        if not self._name:
            raise ValueError("Field name is not set.")
        self.change_field_value(getattr(db_item, self._name, None))

    def apply_description(self: QWidget):  # type: ignore
        """Apply the description to the widget."""
        if self.description:
            self.setToolTip(self.description)
            self.setStatusTip(self.description)

    def change_edit_mode(  # type: ignore
        self: QWidget, in_editing: bool  # type: ignore
    ) -> None:
        """Switch between edit mode and display mode.

        Default implementation sets the enabled state of the widget.

        Args:
            in_editing: True if the field is in edit mode, False if it
                is in display mode.
        """
        self.setEnabled(in_editing)

    def change_field_value(self, new_value: Any) -> None:
        """Change the field value.

        Reimplement this function in subclasses to change the field value.

        Args:
            new_value: The new value to set for the field.
        """
        raise NotImplementedError(
            "change_field_value() must be implemented in subclasses."
        )

    def is_valid(self) -> ValidationResult:
        """Check if the field value is valid.

        By default we check for NULL when the field is not nullable.
        """
        if self._field_value is not None or self.nullable:
            return ValidationResult(
                value=self._field_value,
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
                self.ac_clear.setEnabled(self._field_value is not None)
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
        """Adds a clear to null action to the control.

        The method is called by the `nullable` property setter to create
        a clear to null action.
        The default implementation does nothing.
        """

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

    def getName(self) -> str:
        """Get the name of the field in the database record.

        This is a support function for implementing the name property.
        """
        return self._name

    def setName(self, value: str) -> None:
        """Set the name of the field in the database record.

        This is a support function for implementing the name property.
        """
        self._name = value

    name = pyqtProperty(str, fget=getName, fset=setName)

    def getModifiable(self) -> bool:
        """Get the modifiable property.

        This is a support function for implementing the modifiable property.
        """
        return not self._read_only

    def setModifiable(self, value: bool) -> None:
        """Set the modifiable property.

        This is a support function for implementing the modifiable property.
        """
        self._read_only = not value

    modifiable = pyqtProperty(bool, fget=getModifiable, fset=setModifiable)

    @property
    def read_only(self) -> bool:
        """Get the read_only property."""
        return self._read_only

    @read_only.setter
    def read_only(self, value: bool) -> None:
        """Set the read_only property."""
        if self._read_only != value:
            self._read_only = value
            self.change_read_only(value)

    def change_read_only(self, value: bool) -> None:
        """React to the read_only property being changed."""
        self.setEnabled(not value)  # type: ignore
