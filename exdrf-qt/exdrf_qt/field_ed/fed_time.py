from datetime import date, datetime, time
from typing import Any

from exdrf_qt.field_ed.base_date import DateBase


class DrfTimeEditor(DateBase):
    """Editor for time."""

    def __init__(self, parent=None, format: str = "HH:mm:ss", **kwargs) -> None:
        super().__init__(parent=parent, format=format, **kwargs)

    def change_field_value(self, new_value: Any) -> None:
        """Change the field value.

        Args:
            new_value: The new value to set. If None, the field is set to NULL.
        """
        if new_value is None:
            self.set_line_null()
        else:
            if isinstance(new_value, date) and not isinstance(
                new_value, datetime
            ):
                new_value = time(0, 0, 0, 0)
            elif isinstance(new_value, datetime):
                new_value = new_value.time()
            self.field_value = new_value
            self.set_line_normal()
            self.setText(self.formatter.moment_to_string(new_value))
            if self.nullable:
                assert self.ac_clear is not None
                self.ac_clear.setEnabled(True)

    @property
    def field_value(self) -> Any:
        """Get the field value."""
        if isinstance(self._field_value, datetime):
            return self._field_value.time()
        return self._field_value

    @field_value.setter
    def field_value(self, value: Any) -> None:
        """Set the field value."""
        self._change_field_value(value)


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

    editor1 = DrfTimeEditor(
        ctx=ctx, format="SSS", nullable=True, description="Nullable date"
    )
    editor1.change_field_value(None)

    editor2 = DrfTimeEditor(
        ctx=ctx,
        format="HH:mm:ss.SSS",
        nullable=False,
        description="Non-nullable date",
    )
    editor2.change_field_value(None)

    editor3 = DrfTimeEditor(
        ctx=ctx,
        format="HH:mm",
        nullable=True,
        description="With short",
    )
    editor3.change_field_value(time(12, 30, 45))

    editor3 = DrfTimeEditor(
        ctx=ctx,
        format="The hour is HH and mm minutes",
        nullable=True,
        description="With date and time",
    )
    editor3.change_field_value(time(13, 30, 45))

    layout.addWidget(editor1)
    layout.addWidget(editor2)
    layout.addWidget(editor3)

    main_window.setLayout(layout)
    main_window.show()
    app.exec_()
