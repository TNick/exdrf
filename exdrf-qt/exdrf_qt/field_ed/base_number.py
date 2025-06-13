from typing import Any, Generic, Optional, TypeVar, cast

from exdrf.validator import ValidationResult
from PyQt5.QtCore import Qt

from exdrf_qt.field_ed.base_line import LineBase

T = TypeVar("T", int, float)


class NumberBase(LineBase, Generic[T]):
    """Base for classes that deal with numbers.

    Attributes:
        prefix: Optional prefix to be added to the number.
        suffix: Optional suffix to be added to the number.
        minimum: Minimum value for the number (inclusive).
        maximum: Maximum value for the number (inclusive).
        step: Step size for the number.
    """

    prefix: Optional[str] = None
    suffix: Optional[str] = None
    minimum: Optional[T] = None
    maximum: Optional[T] = None
    step: Optional[T] = None

    def __init__(
        self,
        prefix: Optional[str] = None,
        suffix: Optional[str] = None,
        minimum: Optional[T] = None,
        maximum: Optional[T] = None,
        step: Optional[T] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.prefix = prefix
        self.suffix = suffix
        self.minimum = minimum
        self.maximum = maximum
        self.step = step

        self.textChanged.connect(self.on_text_changed)
        self.editingFinished.connect(self.on_editing_finished)

        if self.nullable:
            self.add_clear_to_null_action()

    def validate(self, text: str) -> Optional[T]:
        """Validates the text and returns the number if valid."""
        raise NotImplementedError("Subclasses must implement this method.")

    def stringify(self, value: T) -> str:
        """Converts the number to a string."""
        return str(value)

    def _check_value(self, text: str) -> ValidationResult:
        result = self.validate(text)
        if result is None:
            return ValidationResult(
                reason="NUMBER",
                error=self.t("cmn.err.invalid_number", "Invalid number"),
            )
        elif self.minimum is not None and result < self.minimum:
            return ValidationResult(
                reason="SMALL",
                error=self.t("cmn.err.too_small", "Value is too small"),
            )
        elif self.maximum is not None and result > self.maximum:
            return ValidationResult(
                reason="LARGE",
                error=self.t("cmn.err.too_large", "Value is too large"),
            )
        else:
            return ValidationResult(
                value=result,
            )

    def check_value(self, text: Any) -> Optional[T]:
        result = self._check_value(text)
        if result.is_valid:
            self.set_line_normal()
            return cast(T, result.value)

        assert result.error is not None
        self.set_line_error(result.error)
        return None

    def on_text_changed(self, text: str) -> None:
        self._on_text_changed(text, False)

    def on_editing_finished(self) -> None:
        """Handles the editing finished signal."""
        self._on_text_changed(self.text(), True)

    def get_stripped_text(self, text: str) -> str:
        text = text.strip()
        if len(text) == 0:
            return text

        if self.prefix:
            prefix = self.prefix.strip()
            if text.startswith(prefix):
                text = text[len(prefix) :].strip()  # noqa: E203

        if self.suffix:
            suffix = self.suffix.strip()
            if text.endswith(suffix):
                text = text[: -len(suffix)].strip()

        return text

    def _on_text_changed(self, text: str, final: bool) -> None:
        """Handles text changes in the line edit."""
        text = self.get_stripped_text(text)
        if len(text) == 0:
            self.set_line_empty()
            return

        result = self.check_value(text)
        if final:
            self.field_value = result

    def change_field_value(self, new_value: Any) -> None:
        """Change the field value.

        Args:
            new_value: The new value to set. If None, the field is set to NULL.
        """
        if new_value is None:
            self.set_line_null()
        else:
            result = self.check_value(str(new_value))
            if result is not None:
                self.field_value = result

                new_value = self.stringify(new_value)
                if self.prefix:
                    new_value = f"{self.prefix}{new_value}"
                if self.suffix:
                    new_value = f"{new_value}{self.suffix}"
                self.setText(new_value)
                if self.nullable:
                    assert self.ac_clear is not None
                    self.ac_clear.setEnabled(True)

    def set_line_null(self):
        """Sets the value of the control to NULL.

        If the control does not support null values, the control will enter
        the error state.
        """
        self.field_value = None
        self.set_line_empty()
        if self.nullable:
            assert self.ac_clear is not None
            self.ac_clear.setEnabled(False)

    def change_by_delta(self, delta: int) -> None:
        """Change the field value by a delta.

        Args:
            delta: The delta to add to the current value.
        """
        value = self.validate(self.get_stripped_text(self.text()))
        if value is None:
            if self.minimum is None:
                self.change_field_value(0)
            else:
                self.change_field_value(self.minimum)
        else:
            if self.step is None:
                step = 1
            else:
                step = self.step
            if delta > 0:
                new_value = value + step
            else:
                new_value = value - step
            if self.minimum is not None and new_value < self.minimum:
                new_value = self.minimum
            if self.maximum is not None and new_value > self.maximum:
                new_value = self.maximum
            self.change_field_value(new_value)

    def keyPressEvent(self, event):
        if self.isReadOnly():
            return super().keyPressEvent(event)

        if event.key() == Qt.Key.Key_Up:
            self.change_by_delta(1)
            event.accept()
        elif event.key() == Qt.Key.Key_Down:
            self.change_by_delta(-1)
            event.accept()
        else:
            return super().keyPressEvent(event)  # type: ignore[override]

    def wheelEvent(self, event):  # type: ignore[override]
        if self.isReadOnly():
            return super().wheelEvent(event)
        if self.hasFocus():
            if event.angleDelta().y() > 0:
                self.change_by_delta(1)
            else:
                self.change_by_delta(-1)
        event.accept()

    def validate_control(self) -> ValidationResult:
        """Check if the field value is valid."""
        if self._field_value is None:
            if not self.nullable:
                return ValidationResult(
                    reason="NULL",
                    error=self.null_error(),
                )
            return ValidationResult(
                value=self._field_value,
            )
        return self._check_value(self.text())

    def is_valid(self) -> bool:
        """Check if the field value is valid."""
        return self.validate_control().is_valid
