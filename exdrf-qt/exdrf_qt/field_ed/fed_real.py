from typing import Optional

from exdrf_qt.field_ed.base_number import NumberBase
from exdrf_qt.field_ed.choices_mixin import EditorWithChoices


class DrfRealEditor(NumberBase[float], EditorWithChoices):
    """Editor for real numbers."""

    decimals: int

    def __init__(self, decimals: int = 2, **kwargs) -> None:
        super().__init__(**kwargs)
        self.decimals = decimals

    def validate(self, text: str) -> Optional[float]:
        """Validates the text and returns the number if valid."""
        if len(text) == 0:
            return None
        try:
            return float(text)
        except ValueError:
            return None

    def stringify(self, value: float) -> str:
        """Converts the number to a string."""
        return f"{value:.{self.decimals}f}" if value is not None else ""


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
    editor1 = DrfRealEditor(
        ctx=ctx, nullable=True, description="Nullable real number"
    )
    editor1.change_field_value(None)

    editor2 = DrfRealEditor(
        ctx=ctx,
        nullable=False,
        description="Non-nullable real number",
        decimals=3,
    )
    editor2.change_field_value(None)

    editor3 = DrfRealEditor(
        ctx=ctx,
        prefix="Prefix ",
        suffix=" Suffix",
        minimum=0,
        maximum=100,
        nullable=True,
        decimals=4,
        step=0.001,
    )
    editor3.change_field_value(12)

    layout.addWidget(editor1)
    layout.addWidget(editor2)
    layout.addWidget(editor3)

    main_window.setLayout(layout)
    main_window.show()
    app.exec_()
