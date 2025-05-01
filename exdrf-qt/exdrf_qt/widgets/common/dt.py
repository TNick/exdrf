from PyQt5.QtCore import QDate, QDateTime, QTime

from exdrf_qt.widgets.common.calendar_popup import CalendarPopup
from exdrf_qt.widgets.common.dt_base import BaseLineEdit


class DateTimeLineEdit(BaseLineEdit):
    """Line edit for datetime values."""

    def __init__(self, parent=None, **kwargs):
        super().__init__("dd-MM-yyyy HH:mm:ss", parent, **kwargs)
        self.calendar_action.setVisible(True)

    def try_parse(self, text):
        dt = QDateTime.fromString(text.strip(), self._format)
        return dt if dt.isValid() else None

    def set_now(self):
        self._value = QDateTime.currentDateTime()
        self._is_null = False
        self.setText(self._value.toString(self._format))
        self.set_valid()

    def adjust_component(self, pos, delta):
        if self._value is None or not self._value.isValid():
            return
        dt = self._value
        if pos <= 2:
            dt = dt.addDays(delta)
        elif pos <= 5:
            dt = dt.addMonths(delta)
        elif pos <= 10:
            dt = dt.addYears(delta)
        elif pos <= 13:
            dt = dt.addSecs(delta * 3600)
        elif pos <= 16:
            dt = dt.addSecs(delta * 60)
        else:
            dt = dt.addSecs(delta)
        self._value = dt
        self.setText(dt.toString(self._format))
        self.set_valid()
        self.setCursorPosition(pos)

    def show_calendar(self):
        popup = CalendarPopup(
            (
                self._value.date()
                if self._value is not None
                else QDate.currentDate()
            ),
            self,
        )
        if popup.exec_():
            date = popup.selectedDate()
            if self._value is None or not self._value.isValid():
                self._value = QDateTime(date, QTime.currentTime())
            else:
                self._value.setDate(date)
            self._is_null = False
            self.setText(self._value.toString(self._format))
            self.set_valid()
