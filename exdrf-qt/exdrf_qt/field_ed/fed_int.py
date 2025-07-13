from typing import Optional

from exdrf_qt.field_ed.base_number import NumberBase
from exdrf_qt.field_ed.choices_mixin import EditorWithChoices


class DrfIntEditor(NumberBase[int], EditorWithChoices):
    """Editor for integer numbers."""

    def validate(self, text: str) -> Optional[int]:
        """Validates the text and returns the number if valid."""
        if len(text) == 0:
            return None
        try:
            return int(text)
        except ValueError:
            return None


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget

    from exdrf_qt.context import QtContext as LocalContext

    # Create the main window
    app = QApplication([])
    main_window = QWidget()
    main_window.setWindowTitle("DrfIntEditor Example")

    ctx = LocalContext(c_string="sqlite:///:memory:")

    # Create a layout and add three DrfBlobEditor controls
    layout = QVBoxLayout()
    editor1 = DrfIntEditor(
        ctx=ctx, nullable=True, description="Nullable integer"
    )
    editor1.change_field_value(None)

    editor2 = DrfIntEditor(
        ctx=ctx, nullable=False, description="Non-nullable integer"
    )
    editor2.change_field_value(None)

    editor3 = DrfIntEditor(
        ctx=ctx,
        prefix="Prefix ",
        suffix=" Suffix",
        minimum=0,
        maximum=100,
        step=1,
        nullable=True,
    )
    editor3.change_field_value(12)

    layout.addWidget(editor1)
    layout.addWidget(editor2)
    layout.addWidget(editor3)

    main_window.setLayout(layout)
    main_window.show()
    app.exec_()
