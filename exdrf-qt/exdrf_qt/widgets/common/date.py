from PyQt5.QtCore import QDate

from exdrf_qt.widgets.common.calendar_popup import CalendarPopup
from exdrf_qt.widgets.common.dt_base import BaseLineEdit


class DateLineEdit(BaseLineEdit):
    """Line edit for date values."""

    def __init__(self, parent=None, **kwargs):
        super().__init__("dd-MM-yyyy", parent, **kwargs)
        self.calendar_action.setVisible(True)

    def try_parse(self, text):
        dt = QDate.fromString(text.strip(), self._format)
        return dt if dt.isValid() else None

    def set_now(self):
        self._value = QDate.currentDate()
        self._is_null = False
        self.setText(self._value.toString(self._format))
        self.set_valid()

    def adjust_component(self, pos, delta):
        if self._value is None or not self._value.isValid():
            return
        d = self._value
        if pos <= 2:
            d = d.addDays(delta)
        elif pos <= 5:
            d = d.addMonths(delta)
        else:
            d = d.addYears(delta)
        self._value = d
        self.setText(d.toString(self._format))
        self.set_valid()
        self.setCursorPosition(pos)

    def show_calendar(self):
        popup = CalendarPopup(self._value or QDate.currentDate(), self)
        if popup.exec_():
            self._value = popup.selectedDate()
            self._is_null = False
            self.setText(self._value.toString(self._format))
            self.set_valid()
