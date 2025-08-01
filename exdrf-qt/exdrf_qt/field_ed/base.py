import logging
from typing import TYPE_CHECKING, Any, Optional

from exdrf.validator import ValidationResult
from PyQt5.QtCore import pyqtProperty, pyqtSignal  # type: ignore
from PyQt5.QtWidgets import QWidget

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext
    from exdrf_qt.controls.base_editor import ExdrfEditor


logger = logging.getLogger(__name__)


class DrfFieldEd(QtUseContext):
    """Base class for field editor widgets.

    Attributes:
        name: the member of the database model that this field editor is for.
            This is used by the `save_value_to()` method to save the current
            value to the database. `ExdrfEditor` uses that method to provide a
            default way of transferring the data from the editor to the
            database model.
        field_value: The value of the field. This is a property that, when set,
            will emit the `controlChanged` signal.
        nullable: Indicates if the field can be null.
        read_only: Indicates if the field is read only.
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
    form: Optional["ExdrfEditor"] = None

    controlChanged = pyqtSignal()
    enteredErrorState = pyqtSignal(str)

    def __init__(  # type: ignore
        self,
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
        self.form = None
        self.apply_description()  # type: ignore

    def set_form(self, form: "ExdrfEditor"):
        """Set the form that this field editor is part of."""
        self.form = form

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

    def save_value_to(self, record: Any):
        """Save the field value into the target record.

        Attributes:
            record: The item to save the field value to.
        """
        if not self._name:
            raise ValueError("Field name is not set.")

        logger.log(
            10,
            "Saving field value %s to record: %s",
            self.field_value,
            self._name,
        )
        setattr(record, self._name, self.field_value)

    def load_value_from(self, record: Any):
        """Load the field value from the database record.

        Attributes:
            record: The item to load the field value from.
        """
        if not self._name:
            raise ValueError("Field name is not set.")
        self.change_field_value(getattr(record, self._name, None))

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

    def validate_control(self) -> ValidationResult:
        """Check if the field value is valid.

        By default we check for NULL when the field is not nullable.
        """
        if self._field_value is None:
            if not self.nullable:
                return ValidationResult(
                    reason="NULL",
                    error=self.null_error(),
                )
        return ValidationResult(value=self._field_value)

    def is_valid(self) -> bool:
        """Check if the field value is valid.

        By default we check for NULL when the field is not nullable.
        """
        return self.validate_control().is_valid

    def null_error(self):
        """Create the error message for NULL when the field is not nullable."""
        return self.t("cmn.err.field_is_empty", "Field cannot be empty")

    @property
    def nullable(self) -> bool:
        """Get the nullable property."""
        return self._nullable

    @nullable.setter
    def nullable(self, value: bool) -> None:
        """Set the nullable property.

        The default implementation looks for an attribute called ac_clear
        in itself and, if found, assumes it is a QAction.
        """
        self.change_nullable(value)

    def change_nullable(self, value: bool) -> None:
        """Set the nullable property.

        The default implementation looks for an attribute called ac_clear
        in itself and, if found, assumes it is a QAction.
        """
        self._nullable = value
        if (
            hasattr(self, "ac_clear")
            and self.ac_clear is not None  # type: ignore
        ):
            # We have an action to clear the field...
            if value:
                # ... and so we should.
                self.ac_clear.setEnabled(  # type: ignore
                    self._field_value is not None
                )
            else:
                # ... but we should not.
                self.ac_clear.deleteLater()  # type: ignore
                self.ac_clear = None
        else:
            # We don't have an action to clear the field...
            if value:
                # ... but we should have one.
                self.add_clear_to_null_action()
            # else:
            #    ... and we should not so all is well in the world.
            #    pass

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

    def starting_new_dependent(self, editor: "ExdrfEditor") -> None:
        """React to the starting of a new editor for creating a new resource
        that will be related to current resource.

        Default implementation sets the parent form of the editor to the form
        that this field editor is part of.

        Args:
            editor: The editor that is starting.
        """
        if self.form is not None:
            editor.on_create_new_dependent(self.form)
