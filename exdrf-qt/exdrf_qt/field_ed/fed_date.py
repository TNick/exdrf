from datetime import datetime
from typing import Any

from PyQt5.QtWidgets import QLineEdit

from exdrf_qt.field_ed.base_date import DateBase


class DrfDateEditor(DateBase):
    """Editor for dates."""

    def __init__(self, parent=None, **kwargs) -> None:
        super().__init__(parent=parent, **kwargs)
        self.addAction(
            self.create_calendar_action(),
            QLineEdit.ActionPosition.TrailingPosition,
        )

    def change_field_value(self, new_value: Any) -> None:
        """Change the field value.

        Args:
            new_value: The new value to set. If None, the field is set to NULL.
        """
        if new_value is None:
            self.set_line_null()
        else:
            if isinstance(new_value, datetime):
                new_value = new_value.date()
            self.field_value = new_value
            self.set_line_normal()
            self.setText(self.formatter.moment_to_string(new_value))
            if self.nullable:
                self.ac_clear.setEnabled(True)


if __name__ == "__main__":
    from datetime import date

    from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget

    from exdrf_qt.context import QtContext as LocalContext

    # Create the main window
    app = QApplication([])
    main_window = QWidget()
    main_window.setWindowTitle("DrfBoolEditor Example")

    ctx = LocalContext(c_string="sqlite:///:memory:")

    # Create a layout and add three DrfBlobEditor controls
    layout = QVBoxLayout()

    editor1 = DrfDateEditor(
        ctx=ctx, format="YYYY", nullable=True, description="Nullable date"
    )
    editor1.change_field_value(None)

    editor2 = DrfDateEditor(
        ctx=ctx,
        format="DD-MM-YYYY",
        nullable=False,
        description="Non-nullable date",
    )
    editor2.change_field_value(None)

    editor3 = DrfDateEditor(
        ctx=ctx, format="YYYY-MM-DD", nullable=True, description="With date"
    )
    editor3.change_field_value(date(2023, 10, 1))

    layout.addWidget(editor1)
    layout.addWidget(editor2)
    layout.addWidget(editor3)

    main_window.setLayout(layout)
    main_window.show()
    app.exec_()
