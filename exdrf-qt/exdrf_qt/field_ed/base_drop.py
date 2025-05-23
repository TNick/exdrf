from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QAction,
    QLineEdit,
    QWidget,
)

from exdrf_qt.field_ed.base_line import LineBase


class DropBase(LineBase):
    """Line edit with combo box-like behavior."""

    dropdown_action: QAction
    _dropdown: QWidget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add dropdown button.
        self.dropdown_action = self.create_drop_down_action()

        # Add an action to set the field to null.
        if self.nullable:
            self.add_clear_to_null_action()

    def change_edit_mode(self, in_editing: bool) -> None:
        super().change_edit_mode(in_editing)
        self.dropdown_action.setEnabled(in_editing and not self._read_only)

    def create_drop_down_action(self) -> QAction:
        """Creates a drop down action for the line edit."""
        action = QAction(self)
        action.setIcon(self.get_icon("bullet_arrow_down"))
        action.triggered.connect(self._toggle_dropdown)
        self.addAction(action, QLineEdit.TrailingPosition)
        self.dropdown_action = action
        return action

    def _show_floating_label(self):
        if self._dropdown.isVisible():
            self.btm_tip.hide()
        else:
            super()._show_floating_label()

    def _toggle_dropdown(self):
        """Show or hide the dropdown list."""
        if self._read_only:
            return
        if self._dropdown.isVisible():
            self._dropdown.hide()
        else:
            self._show_dropdown()

    def set_line_null(self):
        """Sets the line edit to null."""
        if self._read_only:
            return
        self.field_value = None
        self.setText("")
        self.set_line_empty()
        if self.nullable:
            assert self.ac_clear is not None
            self.ac_clear.setEnabled(False)

    def _position_dropdown(self):
        # Position the dropdown below the line edit
        pos = self.mapToGlobal(self.rect().bottomLeft())
        self._dropdown.move(pos)
        self._dropdown.resize(self.width(), self._dropdown.sizeHint().height())
        self._dropdown.show()
        # self.btm_tip.hide()
        QTimer.singleShot(10, lambda: self.setFocus())  # type: ignore[arg-type]
