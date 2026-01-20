from typing import TYPE_CHECKING, Optional, cast

from PyQt5.QtCore import QEvent, QPoint, QRect, Qt, pyqtSignal
from PyQt5.QtWidgets import QAction, QLabel, QLineEdit, QVBoxLayout, QWidget

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QCompleter

from exdrf_qt.field_ed.base import DrfFieldEd


class InfoLabel(QLabel):
    last_label_rect: QRect
    hover_hidden: bool
    is_error: bool

    def __init__(self, parent=None, text: Optional[str] = ""):
        super().__init__(parent=parent)
        self.last_label_rect = QRect()
        self.hover_hidden = False

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

    @property
    def is_empty(self) -> bool:
        """Returns True if the label is empty."""
        return not self.text()

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

        # remember where it was on screen
        self.last_label_rect = self.frameGeometry()
        self.update()

        if len(self.text()) == 0:
            self.hide()

    def show_text(self, text: str):
        self.setText(text)
        self.update_style(False)
        self.is_error = False

    def show_error(self, text: str):
        self.setText(text)
        self.update_style(True)
        self.is_error = True

    def is_inside(self, pos):
        return self.last_label_rect.isValid() and self.last_label_rect.contains(
            pos
        )

    def update_position(self, other):
        if not self.isVisible():
            return
        h = self.sizeHint().height()
        global_pos = other.mapToGlobal(QPoint(0, -h - 2))
        self.move(global_pos)
        self.resize(other.width(), h)
        self.last_label_rect = self.frameGeometry()


class SpecialLine(QLineEdit):

    def keyPressEvent(self, event):  # type: ignore[override]
        result = super().keyPressEvent(event)
        # if event.key() == Qt.Key.Key_Escape:
        #     self.btm_tip.hide()
        #     self.clearFocus()
        if (
            event.type() == QEvent.Type.KeyPress
            and event.key() == Qt.Key.Key_Space
            and (event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        ):
            cast("LineBase", self.parentWidget()).showChoices.emit()
        return result


class LineBase(QWidget, DrfFieldEd):
    """Base for classes that are based on line edit controls."""

    c_line: "SpecialLine"
    c_info: "InfoLabel"
    lay_main: "QVBoxLayout"

    ac_clear: Optional[QAction] = None  # type: ignore
    showChoices = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lay_main = QVBoxLayout(self)
        self.lay_main.setContentsMargins(0, 0, 0, 0)

        self.c_line = SpecialLine(self)
        self.lay_main.addWidget(self.c_line)

        self.c_info = InfoLabel(self)
        self.lay_main.addWidget(self.c_info)

        self.setLayout(self.lay_main)
        # self.btm_tip = InfoLabel(parent=self, text=self.description)

        # watch for global mouse‑moves
        # cast(QApplication, QApplication.instance()).installEventFilter(self)

        # Enable or disable the clear to null action depending on the
        # presence of text in the line edit.
        self.c_line.textChanged.connect(self.change_clear_action)
        self.textChanged = self.c_line.textChanged
        self.returnPressed = self.c_line.returnPressed
        self.textEdited = self.c_line.textEdited
        self.editingFinished = self.c_line.editingFinished
        self.selectionChanged = self.c_line.selectionChanged
        self.cursorPositionChanged = self.c_line.cursorPositionChanged

    def change_clear_action(self, text: str):
        """Enable or disable the clear to null action depending on the text."""
        if hasattr(self, "ac_clear") and self.ac_clear is not None:
            self.ac_clear.setEnabled(bool(text) and not self._read_only)

    def apply_description(self):
        """Apply the description to the widget."""
        if self.description:
            self.tooltip_text = self.description
            self.setStatusTip(self.description)
            self.c_line.setToolTip(self.description)

    def change_edit_mode(self, in_editing: bool) -> None:
        self.c_line.setReadOnly(not in_editing and not self._read_only)
        if self.nullable:
            assert self.ac_clear is not None
            self.ac_clear.setEnabled(in_editing and not self._read_only)

    def set_line_empty(self):
        """Changes the aspect of the line edit to indicate that it is null.

        The control also issues a signal:
        - controlChanged: if NULL is an acceptable value for the field.
        - enteredErrorState: if NULL is not an acceptable value for the field.
        """
        self.c_line.setText("")
        if self.nullable:
            self.c_line.setStyleSheet(
                "QLineEdit { color: gray; font-style: italic; } "
            )
            self.c_line.setPlaceholderText(self.t("cmn.NULL", "NULL"))
            self.controlChanged.emit()
        else:
            self.c_line.setStyleSheet(
                "QLineEdit { color: red; font-style: italic; } "
            )
            self.c_line.setPlaceholderText(self.t("cmn.Empty", "Empty"))

            error = self.null_error()
            self.update_tooltip(error, error=True)
            self.enteredErrorState.emit(error)

    def set_line_normal(self):
        """Changes the aspect of the line edit to indicate that the control has
        a valid value.

        Note that this method does not emit any signal.
        """
        self.c_line.setStyleSheet(
            "QLineEdit { color: black; font-style: normal; } "
        )
        self.c_line.setPlaceholderText("")
        self.update_tooltip(self.description or "")

    def set_line_error(self, error: str):
        """Changes the aspect of the line edit to indicate that the control
        is in an error state.

        The control also issues the error signal.
        """
        self.c_line.setStyleSheet(
            "QLineEdit { color: red; font-style: normal; } "
        )
        self.c_line.setPlaceholderText(self.t("cmn.ERROR", "ERROR"))
        self.update_tooltip(error, error=True)
        self.enteredErrorState.emit(error)

    def update_tooltip(self, text: str, error: bool = False):
        if error:
            self.c_info.show_error(text)
        else:
            self.c_info.show_text(text)
        if len(text) == 0:
            self.c_info.hide()
        else:
            self._show_floating_label()

    def _show_floating_label(self):
        pass
        # self.btm_tip.resize(self.width(), self.btm_tip.sizeHint().height())
        # if self.hasFocus() and not self.btm_tip.is_empty:
        #     self.btm_tip.show()

        # self.btm_tip.update_position(self)

    def add_clear_to_null_action(self):
        """Adds a clear to null action to the line edit."""
        if hasattr(self, "ac_clear") and self.ac_clear is not None:
            # We have an action to clear the field already, so we do nothing.
            return

        self.ac_clear = QAction(
            self.get_icon("clear_to_null"),
            self.t("cmn.clear_to_null", "Clear to NULL"),
            self,
        )
        self.ac_clear.triggered.connect(self.set_line_null)
        self.c_line.addAction(
            self.ac_clear, QLineEdit.ActionPosition.LeadingPosition
        )
        self.ac_clear.setEnabled(
            self.field_value is not None and not self._read_only
        )

    def set_line_null(self):
        """Sets the line edit to null."""
        raise NotImplementedError(
            "set_line_null() must be implemented in subclasses."
        )

    # def focusInEvent(self, event):  # type: ignore[override]
    #     super().focusInEvent(event)
    #     self._show_floating_label()

    # def focusOutEvent(self, event):  # type: ignore[override]
    #     super().focusOutEvent(event)
    #     self.btm_tip.hide()

    # def resizeEvent(self, event):  # type: ignore[override]
    #     super().resizeEvent(event)
    #     self.btm_tip.update_position(self)

    # def moveEvent(self, event):  # type: ignore[override]
    #     super().moveEvent(event)
    #     self.btm_tip.update_position(self)

    # def eventFilter(self, obj, event):  # type: ignore[override]
    #     # 1) intercept hover on the label itself
    #     if obj is self.btm_tip:
    #         if (
    #             event.type() == QEvent.Type.Enter
    #             and not self.btm_tip.hover_hidden
    #         ):
    #             self.btm_tip.hover_hidden = True
    #             self.btm_tip.hide()
    #             return True

    #         # swallow Leave on the label so it doesn’t flicker
    #         # back immediately
    #         if event.type() == QEvent.Type.Leave:
    #             return True

    #     # # 2) watch all mouse‑moves globally

    #     if (
    #         self.btm_tip.hover_hidden
    #         and event.type() == QEvent.Type.MouseMove
    #         and self.hasFocus()
    #     ):
    #         # if the cursor has left the old label rect, show it again
    #         if not self.btm_tip.is_inside(event.globalPos()):
    #             self.hover_hidden = False
    #             self._show_floating_label()
    #         elif self.btm_tip.isVisible():
    #             self.btm_tip.hide()

    #         # don’t block the event
    #         return False

    #     return super().eventFilter(obj, event)

    def change_read_only(self, value: bool) -> None:
        if value:
            if self.ac_clear is not None:
                self.ac_clear.setEnabled(False)
        else:
            if self.ac_clear is not None:
                self.ac_clear.setEnabled(True)
        self.c_line.setReadOnly(value)

    def text(self) -> str:
        return self.c_line.text()

    def setText(self, text: str):
        self.c_line.setText(text)

    def addAction(  # type: ignore
        self, action: QAction, position: QLineEdit.ActionPosition
    ) -> None:  # type: ignore
        self.c_line.addAction(action, position)

    def setReadOnly(self, read_only: bool) -> None:  # type: ignore
        self.c_line.setReadOnly(read_only)

    def isReadOnly(self) -> bool:
        """Return whether the line edit is read-only."""
        return self.c_line.isReadOnly()

    def setPlaceholderText(self, text: str):
        self.c_line.setPlaceholderText(text)

    def setClearButtonEnabled(self, enabled: bool) -> None:
        self.c_line.setClearButtonEnabled(enabled)

    def setMaxLength(self, max_length: int) -> None:
        self.c_line.setMaxLength(max_length)

    def completer(self) -> Optional["QCompleter"]:
        """Return the completer for the line edit."""
        return self.c_line.completer()

    def setCompleter(self, completer: Optional["QCompleter"]) -> None:
        """Set the completer for the line edit."""
        self.c_line.setCompleter(completer)
