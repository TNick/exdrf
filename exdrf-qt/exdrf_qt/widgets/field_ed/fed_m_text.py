from PyQt5.QtWidgets import QPlainTextEdit

from exdrf_qt.widgets.field_ed.fed_base import DBM, QtFieldEditorBase


class DrfTextEditor(QPlainTextEdit, QtFieldEditorBase[DBM]):
    """Text editor for multi-line text fields."""

    def __init__(self, parent=None) -> None:
        self._field_name = []
        self._nullable = False
        super().__init__(parent)
        self._field_name = []

    def read_value(self, record: DBM) -> None:
        value = self._get_value(record)
        self.setPlainText(str(value) if value is not None else "")

    def write_value(self, record: DBM) -> None:
        value = self.toPlainText()
        if value == "":
            value = None
        self._set_value(record, value)

    def clear_to_null(self):
        self.setPlainText("")
        super().clear_to_null()

    def contextMenuEvent(self, e):
        menu = self.createStandardContextMenu()
        assert menu is not None

        self.create_clear_action(menu)

        assert e is not None
        menu.exec_(e.globalPos())
