from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAction, QLineEdit, QStyle

from exdrf_qt.widgets.common.clear_action import create_clear_action
from exdrf_qt.widgets.common.nullable import NullableCtrl


class BaseLineEdit(QLineEdit, NullableCtrl):
    """Base class for date, time, and datetime line edits."""

    def __init__(self, fmt: str, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self._format = fmt
        self._value = None  # Will hold QDate, QTime, or QDateTime

        self.setText("NULL")
        self.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Embedded actions
        self.clear_ac = create_clear_action(self)  # type: ignore
        self.addAction(self.clear_ac, QLineEdit.LeadingPosition)

        style = self.style()  # type: ignore
        assert style is not None
        self.calendar_action = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_ArrowDown),
            "Open Calendar",
        )
        self.calendar_action.triggered.connect(self.show_calendar)
        self.addAction(self.calendar_action, QLineEdit.TrailingPosition)
        self.calendar_action.setVisible(False)  # Enabled only for date types

        # Live validation
        self.textEdited.connect(self.validate_text)

    def clear_to_null(self):
        self._is_null = True
        self._value = None
        self.setText("NULL")
        self.setStyleSheet("QLineEdit { color: gray; font-style: italic; }")

    def set_invalid(self):
        self.setStyleSheet("QLineEdit { color: red; font-style: normal; }")

    def set_valid(self):
        self.setStyleSheet("QLineEdit { color: black; font-style: normal; }")

    def validate_text(self):
        if self.text() == "NULL":
            self._is_null = True
            self._value = None
            self.set_valid()
            return

        parsed = self.try_parse(self.text())
        if parsed:
            self._is_null = False
            self._value = parsed
            self.set_valid()
        else:
            self.set_invalid()

    def try_parse(self, text: str):
        """To be implemented by subclasses"""
        raise NotImplementedError("try_parse not implemented")

    def show_calendar(self):
        """Optional override by subclasses"""
        raise NotImplementedError("show_calendar not implemented")

    def wheelEvent(self, event):  # type: ignore[override]
        if self._is_null:
            self.set_now()
        delta = event.angleDelta().y() // 120
        self.adjust_component(self.cursorPosition(), delta)

    def keyPressEvent(self, event):  # type: ignore[override]
        if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            if self._is_null:
                self.set_now()
            delta = 1 if event.key() == Qt.Key.Key_Up else -1
            self.adjust_component(self.cursorPosition(), delta)
        else:
            super().keyPressEvent(event)

    def adjust_component(self, pos, delta):
        """To be implemented by subclasses"""
        raise NotImplementedError("adjust_component not implemented")

    def set_now(self):
        """To be implemented by subclasses"""
        raise NotImplementedError("set_now not implemented")
