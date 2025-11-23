from typing import Any

from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QFileDialog,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from exdrf_qt.field_ed.base_line import LineBase
from exdrf.field import ExField


class DrfBlobEditor(LineBase):
    """Editor for binary large objects (BLOBs).

    The control is a read-only line edit with two actions: one for uploading a
    file and one for downloading the content of the field to a file. For
    nullable fields the control shows an action for clearing the field to null.

    Attributes:
        ac_download: Action for downloading the file.
        ac_upload: Action for uploading a file.
    """

    ac_download: QAction
    ac_upload: QAction

    def __init__(self, parent=None, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self.setReadOnly(True)
        if self.nullable:
            self.add_clear_to_null_action()

        self.addAction(
            self.create_upload_action(),
            QLineEdit.ActionPosition.TrailingPosition,
        )
        self.addAction(
            self.create_download_action(),
            QLineEdit.ActionPosition.TrailingPosition,
        )

    def change_edit_mode(self, in_editing: bool) -> None:
        super().change_edit_mode(in_editing)
        self.ac_upload.setEnabled(in_editing and not self._read_only)
        self.ac_download.setEnabled(
            in_editing and self.field_value is not None and not self._read_only
        )

    def set_line_null(self):
        """Sets the value of the control to NULL.

        If the control does not support null values, the control will enter
        the error state.
        """
        self.field_value = None
        self.set_line_empty()
        self.ac_download.setEnabled(False)
        if self.nullable:
            assert self.ac_clear is not None
            self.ac_clear.setEnabled(False)

    def change_field_value(self, new_value: Any) -> None:
        """Change the field value.

        Args:
            new_value: The new value to set. If None, the field is set to NULL.
        """
        if new_value is None:
            self.set_line_null()
        else:
            self.field_value = new_value
            self.set_line_normal()
            self.setText(
                self.t("cmn.bytes_length", "({cnt} bytes)", cnt=len(new_value))
            )
            self.ac_download.setEnabled(True)
            if self.nullable:
                assert self.ac_clear is not None
                self.ac_clear.setEnabled(True)

    def create_upload_action(self) -> QAction:
        """Create an action to upload a file."""
        action = QAction(
            self.get_icon("folder"),
            self.t("cmn.upload_file", "Upload File"),
            self,
        )
        action.triggered.connect(self.upload_file)
        self.ac_upload = action
        if self._read_only:
            action.setEnabled(False)
        return action

    def create_download_action(self) -> QAction:
        """Create an action to download a file."""
        action = QAction(
            self.get_icon("download"),
            self.t("cmn.download_file", "Download File"),
            self,
        )
        action.triggered.connect(self.download_file)
        action.setEnabled(False)
        self.ac_download = action
        return action

    def upload_file(self) -> None:
        """Select a file and set it's content as the value."""
        if self._read_only:
            return
        file_name, _ = QFileDialog.getOpenFileName(self, "Select File")
        if file_name:
            with open(file_name, "rb") as f:
                self.change_field_value(f.read())

    def download_file(self) -> None:
        """Select a file and save the content of the value to it."""
        if self.field_value is None:
            return
        file_name, _ = QFileDialog.getSaveFileName(self, "Save File")
        if file_name:
            with open(file_name, "wb") as f:
                if self._data is not None:
                    f.write(self._data)

    def change_read_only(self, value: bool) -> None:
        super().change_read_only(value)
        if self.ac_upload is not None:
            self.ac_upload.setEnabled(not value)

    def create_ex_field(self) -> "ExField":
        from exdrf.field_types.blob_field import BlobField

        return BlobField(
            name=self.name,
            description=self.description or "",
            nullable=self.nullable,
        )


if __name__ == "__main__":
    from exdrf_qt.context import QtContext

    # Create the main window
    app = QApplication([])
    main_window = QWidget()
    main_window.setWindowTitle("DrfBlobEditor Example")

    ctx = QtContext(c_string="sqlite:///:memory:")

    # Create a layout and add three DrfBlobEditor controls
    layout = QVBoxLayout()
    editor1 = DrfBlobEditor(ctx=ctx, nullable=True, description="Nullable BLOB")
    editor1.change_field_value(None)

    editor2 = DrfBlobEditor(
        ctx=ctx, nullable=False, description="Non-nullable BLOB"
    )
    editor2.change_field_value(None)

    editor3 = DrfBlobEditor(ctx=ctx)
    editor3.change_field_value(b"Sample data")

    layout.addWidget(editor1)
    layout.addWidget(editor2)
    layout.addWidget(editor3)

    main_window.setLayout(layout)
    main_window.show()
    app.exec_()
