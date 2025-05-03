from typing import Optional, cast

from PyQt5.QtCore import QEvent, QPoint, QRect, Qt
from PyQt5.QtWidgets import QAction, QApplication, QLabel, QLineEdit

from exdrf_qt.field_ed.base import DrfFieldEd


class InfoLabel(QLabel):
    def __init__(self, parent=None, text: Optional[str] = ""):
        super().__init__(parent=parent)
        self._last_label_rect = QRect()
        self._hover_hidden = False

        self.setText(text)
        self.update_style(False)
        self.setMargin(4)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setWindowFlags(Qt.WindowType.ToolTip)
        self.setWordWrap(True)
        self.setAlignment(
            cast(
                Qt.AlignmentFlag,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            )
        )
        self.hide()

    def update_style(self, with_error: bool):
        self.setStyleSheet(
            "QLabel { "
            f"  color: {'red' if with_error else 'black'};"
            "  background-color: rgb(240,240,255);"
            "  font-size: 9pt;"
            "  border: 1px solid darkgrey;"
            "  border-radius: 6px;"
            "}"
        )

        # reset opacity in case it was hidden by hover
        # self.setWindowOpacity(0.8)

        # remember where it was on screen
        self._last_label_rect = self.frameGeometry()
        self.update()

    def show_text(self, text: str):
        self.setText(text)
        self.update_style(False)

    def show_error(self, text: str):
        self.setText(text)
        self.update_style(True)

    def is_inside(self, pos):
        return (
            self._last_label_rect.isValid()
            and self._last_label_rect.contains(pos)
        )

    def update_position(self, other):
        if not self.isVisible():
            return
        global_pos = other.mapToGlobal(QPoint(0, other.height()))
        self.move(global_pos)
        self.resize(other.width(), self.sizeHint().height())
        self._last_label_rect = self.frameGeometry()


class LineBase(QLineEdit, DrfFieldEd):
    """Base for classes that are based on line edit controls."""

    ac_clear: QAction

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.floating_label = InfoLabel(parent=self, text=self.description)

        # watch for global mouse‑moves
        cast(QApplication, QApplication.instance()).installEventFilter(self)

    def apply_description(self):
        """Apply the description to the widget."""
        if self.description:
            self.tooltip_text = self.description
            self.setStatusTip(self.description)

    def set_line_empty(self):
        """Changes the aspect of the line edit to indicate that it is null.

        The control also issues a signal:
        - controlChanged: if NULL is an acceptable value for the field.
        - enteredErrorState: if NULL is not an acceptable value for the field.
        """
        self.setText("")
        if self.nullable:
            self.setStyleSheet(
                "QLineEdit { color: gray; font-style: italic; } "
            )
            self.setPlaceholderText(self.t("cmn.NULL", "NULL"))
            self.controlChanged.emit()
        else:
            self.setStyleSheet("QLineEdit { color: red; font-style: italic; } ")
            self.setPlaceholderText(self.t("cmn.Empty", "Empty"))

            error = self.null_error()
            self.update_tooltip(error, error=True)
            self.enteredErrorState.emit(error)

    def set_line_normal(self):
        """Changes the aspect of the line edit to indicate that the control has
        a valid value.

        Note that this method does not emit any signal.
        """
        self.setStyleSheet("QLineEdit { color: black; font-style: normal; } ")
        self.setPlaceholderText("")
        self.update_tooltip(self.description or "")

    def set_line_error(self, error: str):
        """Changes the aspect of the line edit to indicate that the control
        is in an error state.

        The control also issues the error signal.
        """
        self.setStyleSheet("QLineEdit { color: red; font-style: normal; } ")
        self.setPlaceholderText(self.t("cmn.ERROR", "ERROR"))
        self.update_tooltip(error, error=True)
        self.enteredErrorState.emit(error)

    def update_tooltip(self, text: str, error: bool = False):
        if error:
            self.floating_label.show_error(text)
        else:
            self.floating_label.show_text(text)
        self._show_floating_label()

    def _show_floating_label(self):
        self.floating_label.resize(
            self.width(), self.floating_label.sizeHint().height()
        )
        if self.hasFocus():
            self.floating_label.show()

        self.floating_label.update_position(self)

    def add_clear_to_null_action(self):
        """Adds a clear to null action to the line edit."""
        self.ac_clear = QAction(
            self.get_icon("clear_to_null"),
            self.t("cmn.clear_to_null", "Clear to NULL"),
            self,
        )
        self.ac_clear.triggered.connect(self.set_line_null)
        self.addAction(self.ac_clear, QLineEdit.ActionPosition.LeadingPosition)

    def set_line_null(self):
        """Sets the line edit to null."""
        raise NotImplementedError(
            "set_line_null() must be implemented in subclasses."
        )

    def focusInEvent(self, event):  # type: ignore[override]
        super().focusInEvent(event)
        self._show_floating_label()

    def focusOutEvent(self, event):  # type: ignore[override]
        super().focusOutEvent(event)
        self.floating_label.hide()

    def resizeEvent(self, event):  # type: ignore[override]
        super().resizeEvent(event)
        self.floating_label.update_position(self)

    def moveEvent(self, event):  # type: ignore[override]
        super().moveEvent(event)
        self.floating_label.update_position(self)

    def keyPressEvent(self, event):  # type: ignore[override]
        super().keyPressEvent(event)
        if event.key() == Qt.Key.Key_Escape:
            self.floating_label.hide()
            self.clearFocus()

    def eventFilter(self, obj, event):  # type: ignore[override]
        # 1) intercept hover on the label itself
        if obj is self.floating_label:
            if (
                event.type() == QEvent.Type.Enter
                and not self.floating_label._hover_hidden
            ):
                self.floating_label._hover_hidden = True
                self.floating_label.hide()
                return True

            # swallow Leave on the label so it doesn’t flicker back immediately
            if event.type() == QEvent.Type.Leave:
                return True

        # 2) watch all mouse‑moves globally

        if (
            self.floating_label._hover_hidden
            and event.type() == QEvent.Type.MouseMove
            and self.hasFocus()
        ):
            # if the cursor has left the old label rect, show it again
            if not self.floating_label.is_inside(event.globalPos()):
                self._hover_hidden = False
                self._show_floating_label()
            elif self.floating_label.isVisible():
                self.floating_label.hide()

            # don’t block the event
            return False

        return super().eventFilter(obj, event)
