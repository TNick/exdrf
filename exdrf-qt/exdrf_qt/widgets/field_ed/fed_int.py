from PyQt5.QtWidgets import QSpinBox

from exdrf_qt.widgets.field_ed.fed_base import DBM, QtFieldEditorBase


class DrfIntEditor(QSpinBox, QtFieldEditorBase[DBM]):
    """Spin editor for integer numbers."""

    def __init__(self, parent=None) -> None:
        self._field_name = []
        self._nullable = False
        self._is_null = False
        super().__init__(parent)

    def read_value(self, record: DBM) -> None:
        value = self._get_value(record)
        if value is None:
            self.clear_to_null()
        else:
            self._is_null = False
            self.setValue(int(value))

    def write_value(self, record: DBM) -> None:
        if self._nullable and self._is_null:
            self._set_value(record, None)
        else:
            value = self.value()
            self._set_value(record, value)

    def clear_to_null(self):
        self.setValue(-1)
        super().clear_to_null()

    def keyPressEvent(self, e):
        if self._nullable and e and e.key() == 16777223:  # Key_Delete
            self.clear_to_null()
        else:
            super().keyPressEvent(e)

    def contextMenuEvent(self, e):
        assert e is not None
        menu = self.createStandardContextMenu()
        self.create_clear_action(menu)
        menu.exec_(e.globalPos())
