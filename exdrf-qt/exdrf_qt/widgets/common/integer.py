from enum import StrEnum
from typing import Any, Optional, Union

from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import QLineEdit

from exdrf_qt.validator import ValidationResult
from exdrf_qt.widgets.common.nullable import NullableCtrl


class ErrReason(StrEnum):
    """Error reasons for validation."""

    NULL = "NULL"
    TYPE = "TYPE"
    INVALID = "INVALID"
    MINIMUM = "MINIMUM"
    MAXIMUM = "MAXIMUM"


class NullableIntegerEdit(QLineEdit, NullableCtrl):
    """A QLineEdit that allows for nullable integer input."""

    _value: Optional[int]
    _null_text: str
    _minimum: Optional[int]
    _maximum: Optional[int]
    _step: int
    _validator: QIntValidator
    _tooltip: Optional[str]

    def __init__(
        self,
        parent=None,
        minimum: Optional[int] = None,
        maximum: Optional[int] = None,
        step: int = 1,
        tooltip: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(parent, **kwargs)
        self._value = None
        self._null_text = "NULL"
        self._minimum = minimum
        self._maximum = maximum
        self._step = step
        self._tooltip = tooltip
        self._validator = QIntValidator()

        self.set_value(None)
        self.editingFinished.connect(self._on_editing_finished)
        self.textChanged.connect(self._on_text_changed)
        self.set_tooltip()
        self.setValidator(self._validator)

    def set_tooltip(self, value: Optional[str] = None):
        if value:
            self.setToolTip(value)
            self.setPlaceholderText(value)
        else:
            self.setToolTip(self._tooltip)
            self.setPlaceholderText(self._tooltip)

    def validate_value(self, in_value: Any) -> ValidationResult[int]:
        result = ValidationResult(None, None, in_value)
        if in_value is None:
            if self._nullable:
                return result
            else:
                result.error = "Value cannot be NULL"
                result.reason = ErrReason.NULL
        elif isinstance(in_value, str):
            in_value = in_value.strip()
            if self._nullable and (
                in_value.upper() == self._null_text or in_value == ""
            ):
                return result

            try:
                value = int(in_value)
                if self._minimum is not None and value < self._minimum:
                    result.error = "Value is less than minimum"
                    result.reason = ErrReason.MINIMUM
                elif self._maximum is not None and value > self._maximum:
                    result.error = "Value is greater than maximum"
                    result.reason = ErrReason.MAXIMUM
            except ValueError:
                result.error = "Invalid integer value"
                result.reason = ErrReason.INVALID
        elif isinstance(in_value, int):
            if self._minimum is not None and in_value < self._minimum:
                result.error = "Value is less than minimum"
                result.reason = ErrReason.MINIMUM
            elif self._maximum is not None and in_value > self._maximum:
                result.error = "Value is greater than maximum"
                result.reason = ErrReason.MAXIMUM
        else:
            result.error = "Invalid type for integer value"
            result.reason = ErrReason.TYPE
        return result

    def set_value(self, value: Union[int, None]):
        r = self.validate_value(value)
        if r.is_valid:
            if self.nullable and r.value is None:
                self._is_null = True
                self._value = None
                self.setStyleSheet(
                    "QLineEdit { color: grey; font-style: italic; }"
                )
                self.setText(self._null_text)
            else:
                self._is_null = False
                self._value = r.value
                self.setStyleSheet(
                    "QLineEdit { color: black; font-style: normal; }"
                )
                self.setText(str(value))
        else:
            self._value = None
            self.setStyleSheet("QLineEdit { color: red; font-style: normal; }")
            self.setText(self._null_text)

    def value(self):
        return self._value

    def _on_editing_finished(self):
        r = self.validate_value(self.text())
        if r.is_valid:
            # TODO
            pass
        text = self.text().strip()
        if text.upper() == self._null_text:
            self.set_value(None)
        else:
            try:
                val = int(text)
                self.set_value(val)
            except ValueError:
                self.setStyleSheet(
                    "QLineEdit { color: red; font-style: normal; }"
                )

    def _on_text_changed(self, text: str):
        text = text.strip()
        if text.upper() == self._null_text:
            return

        error = None
        try:
            value = int(text)
            if self._minimum is not None and value < self._minimum:
                error = "Value is less than minimum"
            elif self._maximum is not None and value > self._maximum:
                error = "Value is greater than maximum"
        except ValueError:
            error = "Invalid integer value"

        if error:
            self.setStyleSheet("QLineEdit { color: red; font-style: normal; }")
        else:
            self.setStyleSheet("QLineEdit { color: red; font-style: normal; }")

    def wheelEvent(self, event):  # type: ignore
        if self._value is None:
            self.set_value(self._minimum)
        if self._value is not None and self.hasFocus():
            delta = event.angleDelta().y()
            if delta > 0:
                self.set_value(self._value + self._step)
            elif delta < 0:
                self.set_value(self._value - 1)
            event.accept()
        else:
            event.ignore()
