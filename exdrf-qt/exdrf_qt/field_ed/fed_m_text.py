from typing import Any, Optional, TYPE_CHECKING

from PyQt5.QtWidgets import QAction, QPlainTextEdit

from exdrf_qt.field_ed.base import DrfFieldEd

if TYPE_CHECKING:
    from exdrf.field import ExField


class DrfTextEditor(QPlainTextEdit, DrfFieldEd):
    """Editor for short strings."""

    ac_clear: QAction
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

        if self.nullable:
            self.add_clear_to_null_action()

    def change_edit_mode(self, in_editing: bool) -> None:
        self.setReadOnly(not in_editing and not self._read_only)

    def add_clear_to_null_action(self):
        """Adds a clear to null action to the line edit."""
        self.ac_clear = QAction(
            self.get_icon("clear_to_null"),
            self.t("cmn.clear_to_null", "Clear to NULL"),
            self,
        )
        self.ac_clear.triggered.connect(self.set_line_null)

    def contextMenuEvent(self, e):
        menu = self.createStandardContextMenu()
        assert menu is not None

        if self.nullable:
            menu.addAction(self.ac_clear)

        assert e is not None
        menu.exec_(e.globalPos())

    def change_field_value(self, new_value: Any) -> None:
        """Change the field value.

        Args:
            new_value: The new value to set. If None, the field is set to NULL.
        """
        if new_value is None:
            self.set_line_null()
        else:
            self.field_value = str(new_value)
            self.setPlainText(str(new_value))

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

    def on_text_changed(self) -> None:
        self._on_text_changed(self.toPlainText(), True)

    def set_line_null(self):
        """Sets the value of the control to NULL.

        If the control does not support null values, the control will enter
        the error state.
        """
        self.field_value = None
        self.set_line_empty()
        if self.nullable:
            self.ac_clear.setEnabled(False)

    def set_line_empty(self):
        """Changes the aspect of the line edit to indicate that it is null.

        The control also issues a signal:
        - controlChanged: if NULL is an acceptable value for the field.
        - enteredErrorState: if NULL is not an acceptable value for the field.
        """
        self.setPlainText("")
        if self.nullable:
            self.setStyleSheet(
                "QPlainTextEdit { color: gray; font-style: italic; } "
            )
            self.setPlaceholderText(self.t("cmn.NULL", "NULL"))
            self.controlChanged.emit()
        else:
            self.setStyleSheet(
                "DrfTextEditor { color: red; font-style: italic; } "
            )
            self.setPlaceholderText(self.t("cmn.Empty", "Empty"))

            error = self.null_error()
            self.update_tooltip(error)
            self.enteredErrorState.emit(error)

    def set_line_normal(self):
        """Changes the aspect of the line edit to indicate that the control has
        a valid value.

        Note that this method does not emit any signal.
        """
        self.setStyleSheet(
            "DrfTextEditor { color: black; font-style: normal; } "
        )
        self.setPlaceholderText("")
        self.update_tooltip(self.description or "")
        if self.nullable:
            self.ac_clear.setEnabled(True)

    def set_line_error(self, error: str):
        """Changes the aspect of the line edit to indicate that the control
        is in an error state.

        The control also issues the error signal.`
        """
        self.setStyleSheet("DrfTextEditor { color: red; font-style: normal; } ")
        self.setPlaceholderText(self.t("cmn.ERROR", "ERROR"))
        self.update_tooltip(error, error=True)
        self.enteredErrorState.emit(error)

    def update_tooltip(self, text: str, error: bool = False):
        self.setToolTip(text)

    def change_read_only(self, value: bool) -> None:
        self.setReadOnly(value)
        if self.ac_clear is not None:
            self.ac_clear.setEnabled(not value and self.field_value is not None)

    def create_ex_field(self) -> "ExField":
        from exdrf.field_types.str_field import StrField

        return StrField(
            name=self.name,
            description=self.description or "",
            multiline=True,
            nullable=self.nullable,
            min_length=self.min_len or 0,
            max_length=self.max_len or 0,
        )


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
    editor1 = DrfTextEditor(
        ctx=ctx, nullable=True, description="Nullable string"
    )
    editor1.change_field_value(None)

    editor2 = DrfTextEditor(
        ctx=ctx, nullable=False, description="Non-nullable string"
    )
    editor2.change_field_value(None)

    editor3 = DrfTextEditor(
        ctx=ctx,
        nullable=True,
        max_len=10,
        min_len=5,
    )
    editor3.change_field_value("abcdef")

    layout.addWidget(editor1)
    layout.addWidget(editor2)
    layout.addWidget(editor3)

    main_window.setLayout(layout)
    main_window.show()
    app.exec_()
