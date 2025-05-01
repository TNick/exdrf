from PyQt5.QtCore import pyqtProperty  # type: ignore


class NullableCtrl:
    """Mixin for controls that may or may not support null values.

    Attributes:
        _nullable: Indicates if the control supports null values.
        _is_null: Indicates if the current value is null.
        nullable: Property to get or set the nullable state of the control.
    """

    _nullable: bool
    _is_null: bool

    def __init__(self) -> None:
        self._nullable = False
        self._is_null = False

    def getNullable(self) -> bool:
        """Tell if the field is nullable."""
        return self._nullable

    def set_nullable_hooks(self, nullable: bool) -> None:
        """Set the nullable property and update the editor accordingly.

        Args:
            nullable: Whether the field is nullable or not.
        """

    def setNullable(self, nullable: bool) -> None:
        """Set the nullable property and update the editor accordingly.

        Because of the way Qt implements properties, the subclass method will
        not be called. O work around this, reimplement set_nullable_hooks
        instead.
        """
        self._nullable = nullable
        clear_ac = getattr(self, "clear_ac", None)
        if clear_ac:
            if nullable:
                clear_ac.setEnabled(not self._is_null)
            else:
                clear_ac.setEnabled(False)
        self.set_nullable_hooks(nullable)

    nullable = pyqtProperty(bool, fget=getNullable, fset=setNullable)
