from typing import Any, Optional

from exdrf_qt.field_ed.base_line import LineBase


class DrfLineEditor(LineBase):
    """Editor for short strings."""

    min_len: Optional[int] = None
    max_len: Optional[int] = None

    def __init__(
        self,
        min_len: Optional[int] = None,
        max_len: Optional[int] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.min_len = min_len
        self.max_len = max_len

        self.textChanged.connect(self.on_text_changed)
        self.editingFinished.connect(self.on_editing_finished)

        if self.nullable:
            self.add_clear_to_null_action()

    def change_field_value(self, new_value: Any) -> None:
        """Change the field value.

        Args:
            new_value: The new value to set. If None, the field is set to NULL.
        """
        if new_value is None:
            self.set_line_null()
        else:
            self.field_value = str(new_value)
            self.setText(str(new_value))

    def check_value(self, text: Any) -> Optional[str]:
        """Check the value of the text.

        Args:
            text: The text to check.

        Returns:
            The validated text or None if invalid.
        """
        if self.min_len is not None and len(text) < self.min_len:
            self.set_line_error(
                self.t(
                    "cmn.err.too_short",
                    "Too short ({crt}). Minimum length is {min_len}.",
                    min_len=self.min_len,
                    crt=len(text),
                )
            )
            return None
        if self.max_len is not None and len(text) > self.max_len:
            self.set_line_error(
                self.t(
                    "cmn.err.too_long",
                    "Too long ({crt}). Maximum length is {max_len}.",
                    max_len=self.max_len,
                    crt=len(text),
                )
            )
            return None
        return text

    def _on_text_changed(self, text: str, final: bool):
        """Handles text changes in the line edit."""
        if self._read_only:
            return
        result = self.check_value(text)
        if result:
            self.set_line_normal()
        if final:
            # Change the value and signal the change.
            self.field_value = result

    def on_text_changed(self, text: str) -> None:
        self._on_text_changed(text, False)

    def on_editing_finished(self) -> None:
        """Handles the editing finished signal."""
        self._on_text_changed(self.text(), True)

    def set_line_null(self):
        """Sets the value of the control to NULL.

        If the control does not support null values, the control will enter
        the error state.
        """
        self.field_value = None
        self.set_line_empty()
        if self.nullable:
            assert self.ac_clear is not None
            self.ac_clear.setEnabled(False)


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget

    from exdrf_qt.context import QtContext as LocalContext

    # Create the main window
    app = QApplication([])
    main_window = QWidget()
    main_window.setWindowTitle("DrfBoolEditor Example")

    ctx = LocalContext(c_string="sqlite:///:memory:")

    # Create a layout and add three DrfBlobEditor controls
    layout = QVBoxLayout()
    editor1 = DrfLineEditor(
        ctx=ctx, nullable=True, description="Nullable string"
    )
    editor1.change_field_value(None)

    editor2 = DrfLineEditor(
        ctx=ctx, nullable=False, description="Non-nullable string"
    )
    editor2.change_field_value(None)

    editor3 = DrfLineEditor(
        ctx=ctx,
        nullable=True,
    )
    editor3.change_field_value("abcdef")

    layout.addWidget(editor1)
    layout.addWidget(editor2)
    layout.addWidget(editor3)

    main_window.setLayout(layout)
    main_window.show()
    app.exec_()
