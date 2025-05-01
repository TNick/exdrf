from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QCheckBox

from exdrf_qt.widgets.field_ed.fed_base import DBM, DrfFieldEditor

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext


class DrfBoolEditor(QCheckBox, DrfFieldEditor[DBM]):
    """Editor for boolean values."""

    true_str: str = "True"
    false_str: str = "False"
    null_str: str = "NULL"

    def __init__(self, ctx: "QtContext", parent=None) -> None:
        super().__init__(parent, ctx=ctx)  # type: ignore
        if self._nullable:
            self.setTristate(True)
        else:
            self.setTristate(False)
        self.stateChanged.connect(self._on_check_state_changed)

    def set_nullable_hooks(self, nullable: bool) -> None:
        if nullable:
            self.setTristate(True)
        else:
            self.setTristate(False)

    def read_value(self, record: DBM) -> None:
        value = self._get_value(record)
        if value is None:
            self.clear_to_null()
        else:
            self._is_null = False
            self.setChecked(value)

    def write_value(self, record: DBM) -> None:
        self._is_null = self.isTristate()
        if self._nullable and self._is_null:
            self._set_value(record, None)
        else:
            value = self.checkState() == Qt.CheckState.Checked
            self._set_value(record, value)

    def _on_check_state_changed(self, state: int) -> None:
        """Handle the check state changed event."""
        if state == Qt.CheckState.PartiallyChecked:
            self._is_null = True
            self.setStyleSheet("color: gray; font-style: italic;")
        else:
            self._is_null = False
            self.setStyleSheet("")
        if state == Qt.CheckState.Checked:
            self.setText(self.true_str)
        elif state == Qt.CheckState.Unchecked:
            self.setText(self.false_str)
        else:
            self.setText(self.null_str)
