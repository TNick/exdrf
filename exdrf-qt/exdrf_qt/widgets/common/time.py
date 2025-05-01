from PyQt5.QtCore import QTime

from exdrf_qt.widgets.common.dt_base import BaseLineEdit


class TimeLineEdit(BaseLineEdit):
    """Line edit for time values."""

    def __init__(self, parent=None, **kwargs):
        super().__init__("HH:mm:ss", parent, **kwargs)

    def try_parse(self, text):
        t = QTime.fromString(text.strip(), self._format)
        return t if t.isValid() else None

    def set_now(self):
        self._value = QTime.currentTime()
        self._is_null = False
        self.setText(self._value.toString(self._format))
        self.set_valid()

    def adjust_component(self, pos, delta):
        if self._value is None or not self._value.isValid():
            return
        t = self._value
        if pos <= 2:
            t = t.addSecs(delta * 3600)
        elif pos <= 5:
            t = t.addSecs(delta * 60)
        else:
            t = t.addSecs(delta)
        self._value = t
        self.setText(t.toString(self._format))
        self.set_valid()
        self.setCursorPosition(pos)
