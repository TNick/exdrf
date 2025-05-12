from datetime import date, datetime
from typing import TypeVar, Union

from exdrf.moment import MomentFormat
from exdrf.validator import ValidationResult
from PyQt5.QtWidgets import (
    QAction,
    QCalendarWidget,
    QDialog,
    QDialogButtonBox,
    QVBoxLayout,
)

from exdrf_qt.field_ed.base_line import LineBase

T = TypeVar("T", date, datetime)


class CalendarPopup(QDialog):
    """A dialog that shows a calendar widget for selecting a date."""

    calendar: QCalendarWidget
    bbox: QDialogButtonBox

    def __init__(self, current_date: T, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Date")

        # Create the calendar widget and set the selected date.
        self.calendar = QCalendarWidget(self)
        self.calendar.setGridVisible(True)
        self.calendar.setSelectedDate(current_date)

        # Add a button box with OK and Cancel buttons.
        self.bbox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self
        )
        self.bbox.accepted.connect(self.accept)
        self.bbox.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.calendar)
        layout.addWidget(self.bbox)

    def selected_date(self) -> date:
        """Returns the selected date."""
        return self.calendar.selectedDate().toPyDate()


class DateBase(LineBase):
    """Base for classes that deal with date and time."""

    formatter: MomentFormat

    def __init__(
        self, format: Union[str, MomentFormat], parent=None, **kwargs
    ) -> None:
        super().__init__(parent, **kwargs)

        if isinstance(format, str):
            self.formatter = MomentFormat.from_string(format)
        else:
            self.formatter = format

        if self.nullable:
            self.add_clear_to_null_action()
        self.textChanged.connect(self._on_text_changed)

    def wheelEvent(self, event):  # type: ignore[override]
        if self.field_value is None:
            self.change_field_value(datetime.now())
        else:
            delta = event.angleDelta().y() // 120
            result = self.formatter.validate(self.text(), self.t)
            if result.is_invalid:
                return
            prev_pos = self.cursorPosition()
            assert result.value is not None
            new_value = self.formatter.apply_offset(
                result.value, prev_pos, delta
            )
            self.change_field_value(new_value)
            self.setCursorPosition(prev_pos)

    def create_calendar_action(self):
        """Creates a calendar action for the line edit."""
        action = QAction(
            self.get_icon("calendar"),
            self.t("cmn.open_calendar", "Open Calendar"),
            self,
        )
        action.triggered.connect(self.open_calendar)
        self.ac_upload = action
        return action

    def open_calendar(self):
        """Opens a calendar dialog."""
        text = self.text()
        result = self.formatter.validate(text, self.t)
        if result.is_invalid:
            current_date = datetime.now()
        else:
            current_date = result.value

        calendar_dialog = CalendarPopup(
            current_date, self  # type: ignore[call-arg]
        )
        if calendar_dialog.exec_() == QDialog.Accepted:
            cal_date = calendar_dialog.selected_date()
            if isinstance(self.field_value, datetime):
                cal_date = datetime(
                    cal_date.year,
                    cal_date.month,
                    cal_date.day,
                    self.field_value.hour,
                    self.field_value.minute,
                    self.field_value.second,
                    self.field_value.microsecond,
                )
            self.change_field_value(cal_date)

    def _on_text_changed(self, text: str) -> None:
        """Handles text changes in the line edit."""
        if len(text) == 0:
            self.set_line_empty()
            return

        result = self.formatter.validate(text, self.t)
        if result.is_invalid:
            assert result.error is not None
            self.set_line_error(result.error)
        else:
            self.set_line_normal()
            self.field_value = result.value

    def on_editing_finished(self) -> None:
        """Handles the editing finished signal."""
        text = self.text()
        if len(text) == 0:
            self.set_line_empty()
            return

        result = self.formatter.validate(text, self.t)
        if result.is_invalid:
            assert result.error is not None
            self.set_line_error(result.error)
        else:
            self.set_line_normal()

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

    def is_valid(self) -> ValidationResult:
        """Check if the field value is valid."""
        if self._field_value is None and not self.nullable:
            return ValidationResult(
                reason="NULL",
                error=self.null_error(),
            )
        return self.formatter.validate(self.text(), self.t)
