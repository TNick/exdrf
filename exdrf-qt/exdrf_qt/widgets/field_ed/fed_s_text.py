from PyQt5.QtWidgets import QLineEdit, QStyle

from exdrf_qt.widgets.field_ed.fed_base import DBM, QtFieldEditorBase


class DrfLineEditor(QLineEdit, QtFieldEditorBase[DBM]):
    """Line editor for single-line text fields."""

    def __init__(self, parent=None) -> None:
        self._field_name = []
        self._nullable = False
        super().__init__(parent)

        # Create a clear_to_null action for the line edit.
        style = self.style()
        assert style is not None
        self.clear_action = self.addAction(
            style.standardIcon(QStyle.StandardPixmap.SP_DialogResetButton),
            QLineEdit.TrailingPosition,
        )
        assert self.clear_action is not None
        self.clear_action.triggered.connect(self.clear_to_null)

    def read_value(self, record: DBM) -> None:
        value = self._get_value(record)
        self.setText(str(value) if value is not None else "")

    def write_value(self, record: DBM) -> None:
        value = self.text()
        if value == "":
            value = None
        self._set_value(record, value)

    def clear_to_null(self):
        self.setText("")
        super().clear_to_null()

    def contextMenuEvent(self, e):  # type: ignore[override]
        menu = self.createStandardContextMenu()
        assert menu is not None
        self.create_clear_action(menu)
        menu.exec_(e.globalPos())
