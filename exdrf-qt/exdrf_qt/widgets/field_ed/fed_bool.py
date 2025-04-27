from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QCheckBox

from exdrf_qt.widgets.field_ed.fed_base import DBM, QtFieldEditorBase


class DrfDateEditor(QCheckBox, QtFieldEditorBase[DBM]):
    """Editor for boolean values."""

    def __init__(self, parent=None) -> None:
        self._field_name = []
        self._nullable = False
        self._is_null = False
        super().__init__(parent)
        if self._nullable:
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
