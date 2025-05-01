from typing import TYPE_CHECKING, Optional

from PyQt5.QtWidgets import QAction, QFileDialog, QLineEdit, QStyle

from exdrf_qt.widgets.field_ed.fed_base import DBM, DrfFieldEditor

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext


class DrfBlobEditor(QLineEdit, DrfFieldEditor[DBM]):
    """Editor for binary large objects (BLOBs)."""

    _data: Optional[bytes]
    ac_download: QAction
    ac_upload: QAction

    def __init__(self, ctx: "QtContext", parent=None) -> None:
        self._data = None
        super().__init__(parent, ctx=ctx)  # type: ignore
        self.setReadOnly(True)
        self.setPlaceholderText("NULL")
        self.setStyleSheet("color: gray; font-style: italic;")

        self.addAction(
            self.create_clear_action(), QLineEdit.ActionPosition.LeadingPosition
        )
        self.addAction(
            self.create_upload_action(),
            QLineEdit.ActionPosition.TrailingPosition,
        )
        self.addAction(
            self.create_download_action(),
            QLineEdit.ActionPosition.TrailingPosition,
        )

    def set_data(self, data: Optional[bytes]) -> None:
        """Set the data for the editor."""
        self._data = data
        if data is None:
            self.clear_to_null()
        else:
            self.setStyleSheet("")
            self.setPlaceholderText(f"({len(data)} bytes)")
            self.ac_download.setEnabled(True)

    def read_value(self, record: DBM) -> None:
        value = self._get_value(record)
        self.set_data(value)

    def write_value(self, record: DBM) -> None:
        self._is_null = self.isTristate()
        if self._nullable and self._is_null:
            self._set_value(record, None)
        else:
            self._set_value(record, self._data)

    def clear_to_null(self):
        super().clear()
        self._data = None
        self.setStyleSheet("color: gray; font-style: italic;")
        self.setPlaceholderText("NULL")
        self.ac_download.setEnabled(False)

    def create_upload_action(self) -> QAction:
        """Create an action to upload a file."""
        action = QAction("Upload File", self)
        style = self.style()
        assert style is not None, "Style should not be None"
        action.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        action.triggered.connect(self.upload_file)
        self.ac_upload = action
        return action

    def create_download_action(self) -> QAction:
        """Create an action to download a file."""
        action = QAction("Download File", self)
        style = self.style()
        assert style is not None, "Style should not be None"
        action.setIcon(
            style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)
        )
        action.triggered.connect(self.download_file)
        action.setEnabled(False)
        self.ac_download = action
        return action

    def upload_file(self) -> None:
        """Select a file and set it's content as the value."""
        file_name, _ = QFileDialog.getOpenFileName(self, "Select File")
        if file_name:
            with open(file_name, "rb") as f:
                self.set_data(f.read())

    def download_file(self) -> None:
        """Select a file and save the content of the value to it."""
        if self._is_null:
            return
        file_name, _ = QFileDialog.getSaveFileName(self, "Save File")
        if file_name:
            with open(file_name, "wb") as f:
                if self._data is not None:
                    f.write(self._data)
