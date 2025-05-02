from typing import TYPE_CHECKING, Any, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QVBoxLayout,
    QWidget,
)

from exdrf_qt.field_ed.base import DrfFieldEd

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext


class DrfBoolEditor(QCheckBox, DrfFieldEd):
    """Editor for boolean values.

    The control is a checkbox that can be checked, unchecked, or in a
    partially checked state. The partially checked state is used to indicate
    that the value is NULL.

    Attributes:
        true_str: The string to display when the value is True.
        false_str: The string to display when the value is False.
        null_str: The string to display when the value is None.
    """

    true_str: str
    false_str: str
    null_str: str

    def __init__(
        self,
        ctx: "QtContext",
        parent=None,
        true_str: Optional[str] = None,
        false_str: Optional[str] = None,
        null_str: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, ctx=ctx, **kwargs)  # type: ignore
        if true_str is None:
            true_str = self.t("cmn.TRUE", "True")
        if false_str is None:
            false_str = self.t("cmn.FALSE", "False")
        if null_str is None:
            null_str = self.t("cmn.NULL", "NULL")
        self.true_str = true_str
        self.false_str = false_str
        self.null_str = null_str

        if self.nullable:
            self.setTristate(True)
        else:
            self.setTristate(False)
        self.stateChanged.connect(self._on_check_state_changed)

    def set_null_value(self) -> None:
        self.field_value = None
        if self.nullable:
            self.setCheckState(Qt.CheckState.PartiallyChecked)
            self.setText(self.null_str)
            self.setStyleSheet("QCheckBox { color: gray; font-style: italic; }")
        else:
            self.setCheckState(Qt.CheckState.Unchecked)
            error = self.null_error()
            self.enteredErrorState.emit(error)
            self.setText(error)
            self.setStyleSheet("QCheckBox { color: red; font-style: normal; }")

    def change_field_value(self, new_value: Any) -> None:
        """Change the field value."""
        if new_value is None:
            self.set_null_value()
            return

        self.field_value = new_value
        if new_value:
            self.setCheckState(Qt.CheckState.Checked)
            self.setText(self.true_str)
        else:
            self.setCheckState(Qt.CheckState.Unchecked)
            self.setText(self.false_str)

        self.setStyleSheet("QCheckBox { color: black; font-style: normal; }")
        self.controlChanged.emit()

    def _on_check_state_changed(self, state: int) -> None:
        """Handle the check state changed event."""
        if state == Qt.CheckState.PartiallyChecked:
            return self.set_null_value()

        self.change_field_value(state == Qt.CheckState.Checked)


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication

    from exdrf_qt.context import QtContext as LocalContext

    # Create the main window
    app = QApplication([])
    main_window = QWidget()
    main_window.setWindowTitle("DrfBoolEditor Example")

    ctx = LocalContext(c_string="sqlite:///:memory:")

    # Create a layout and add three DrfBlobEditor controls
    layout = QVBoxLayout()
    editor1 = DrfBoolEditor(
        ctx=ctx, nullable=True, description="Nullable boolean"
    )
    editor1.change_field_value(None)

    editor2 = DrfBoolEditor(
        ctx=ctx, nullable=False, description="Non-nullable boolean"
    )
    editor2.change_field_value(None)

    editor3 = DrfBoolEditor(
        ctx=ctx,
        true_str="Yes",
        false_str="No",
        null_str="Unknown",
        nullable=True,
    )
    editor3.change_field_value(True)

    layout.addWidget(editor1)
    layout.addWidget(editor2)
    layout.addWidget(editor3)

    main_window.setLayout(layout)
    main_window.show()
    app.exec_()
