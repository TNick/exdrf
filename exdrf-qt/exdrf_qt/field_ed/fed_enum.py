from typing import TYPE_CHECKING, Any, List, Tuple, cast

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QAction,
    QFrame,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.field_ed.base_line import LineBase

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext


class DropdownList(QFrame, QtUseContext):
    """Custom dropdown list widget for DrfEnumEditor.

    Signals:
        itemSelected: Emitted when an item is selected from the list. Takes
            two parameters: the key and the label of the selected item.
    """

    itemSelected = pyqtSignal(str, str)

    def __init__(self, ctx: "QtContext", parent: "DrfEnumEditor"):
        super().__init__(parent)
        self.ctx = ctx

        # Set up the frame
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setWindowFlags(
            cast(
                Qt.WindowType,
                Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint,
            )
        )

        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(1)

        # Create list widget
        self.list_widget = QListWidget(self)
        self.list_widget.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.list_widget.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.list_widget)

        self.setLayout(layout)

    def on_item_clicked(self, item: QListWidgetItem):
        """Handle item selection in the list."""
        key = item.data(Qt.ItemDataRole.UserRole)
        label = item.text()
        if key is None:
            return

        self.itemSelected.emit(key, label)
        self.hide()

    def keyPressEvent(self, event):  # type: ignore[override]
        """Handle keyboard events.

        We select the current item when Enter is pressed and hide the dropdown
        when Escape is pressed. Other keys are passed to the list widget.
        """
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            # Select current item
            current_item = self.list_widget.currentItem()
            if current_item:
                self.on_item_clicked(current_item)
        elif event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            # Pass other keys to the line edit
            # This allows for typing in the line edit while the dropdown is open
            # and also allows for navigation using arrow keys.
            cast("DrfEnumEditor", self.parent()).keyPressEvent(event)

    def populate(self, choices: List[Tuple[str, str]], filter_text: str = ""):
        """Populate the list with filtered choices."""
        self.list_widget.clear()
        filter_text = filter_text.lower()

        # If there is an exact match we show all items.
        show_all = len(filter_text) == 0 or any(
            label.lower() == filter_text for _, label in choices
        )

        lower_ft = filter_text.lower()
        idx = 0
        for key, label in choices:
            low_label = label.lower()
            if show_all or lower_ft in low_label:
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, key)
                if lower_ft == low_label:
                    self.list_widget.setCurrentRow(idx)
                    item.setSelected(True)
                    item.setIcon(self.get_icon("bullet_green"))
                self.list_widget.addItem(item)
                idx += 1

        if idx == 0:
            # No matches found, show a placeholder item
            placeholder_item = QListWidgetItem(
                self.t("cmn.err.no_matches_found", "No matches found")
            )
            placeholder_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_widget.addItem(placeholder_item)

        return True

    def showEvent(self, event):  # type: ignore[override]
        """Adjust size when showing the dropdown."""
        super().showEvent(event)
        # Adjust width to match parent width
        if self.parent():
            self.setMinimumWidth(cast(QWidget, self.parent()).width())

        # Adjust height based on content but cap it
        visible_items = min(10, self.list_widget.count())
        if visible_items > 0:
            item_height = self.list_widget.sizeHintForRow(0)
            self.setMaximumHeight(
                visible_items * item_height + 10
            )  # Add some margin


class DrfEnumEditor(LineBase):
    """Line edit with combo box-like behavior."""

    def __init__(self, *args, choices=None, **kwargs):
        super().__init__(*args, **kwargs)

        # List of (key, label) tuples.
        self.choices = choices or []

        # Stores the currently selected key.
        self.field_value = None

        # Create dropdown list
        self._dropdown = DropdownList(parent=self, ctx=self.ctx)
        self._dropdown.itemSelected.connect(self._on_item_selected)

        # Add dropdown button.
        self.dropdown_action = QAction(self)
        self.dropdown_action.setIcon(self.get_icon("bullet_arrow_down"))
        self.dropdown_action.triggered.connect(self._toggle_dropdown)
        self.addAction(self.dropdown_action, QLineEdit.TrailingPosition)

        # Connect text changed signal to filter the dropdown
        self.textChanged.connect(self._on_text_changed)

        if self.nullable:
            self.add_clear_to_null_action()

    def _toggle_dropdown(self):
        """Show or hide the dropdown list."""
        if self._dropdown.isVisible():
            self._dropdown.hide()
        else:
            self._show_dropdown()

    def _show_floating_label(self):
        if self._dropdown.isVisible():
            self.btm_tip.hide()
        else:
            super()._show_floating_label()

    def _position_dropdown(self):
        # Position the dropdown below the line edit
        pos = self.mapToGlobal(self.rect().bottomLeft())
        self._dropdown.move(pos)
        self._dropdown.show()
        self.btm_tip.hide()
        QTimer.singleShot(10, lambda: self.setFocus())  # type: ignore[arg-type]
        # Set focus back to the line edit after showing the dropdown
        # self.setFocus()
        # self._dropdown.setFocus()

    def _show_dropdown(self):
        """Show the dropdown with filtered choices."""
        if not self.choices:
            return

        # Populate with filtered choices
        if self._filter_choices(self.text()):
            self._position_dropdown()

    def _filter_choices(self, text: str) -> bool:
        """Filter choices based on the current text.

        Returns:
            True if there are matches.
        """
        return self._dropdown.populate(self.choices, text)

    def _on_text_changed(self, text: str):
        """Handle text changes."""
        have_choices = self._filter_choices(text)

        # Always show dropdown when typing if there are choices
        if have_choices:
            if not self._dropdown.isVisible():
                self._position_dropdown()
        else:
            # Only hide if no matches
            self._dropdown.hide()

        # Clear the selected key when text changes manually
        self.field_value = None

        # Check if the entered text exactly matches any of the choice labels
        for key, label in self.choices:
            if label.lower() == text.lower():  # Case-insensitive matching
                self.field_value = key
                self.set_line_normal()
                self.controlChanged.emit()
                return

        # If we get here, the text doesn't match any choice exactly
        if text:
            self.set_line_normal()  # Allow typing to continue
        else:
            self.set_line_empty()

    def _on_item_selected(self, key: str, label: str):
        """Handle selection from the dropdown."""
        self.field_value = key
        self.setText(label)
        self.set_line_normal()
        self.controlChanged.emit()
        self.setFocus()  # Return focus to line edit after selection

    def set_line_null(self):
        """Sets the line edit to null."""
        self.field_value = None
        self.setText("")
        self.set_line_empty()

    def set_choices(self, choices: List[Tuple[str, str]]):
        """Set the available choices."""
        self.choices = choices
        # Clear the current selection if it's no longer in the choices
        if self.field_value:
            if not any(key == self.field_value for key, _ in choices):
                self.set_line_null()

    def change_field_value(self, new_value: Any) -> None:
        """Change the field value.

        Args:
            new_value: The new value to set. If None, the field is set to NULL.
        """
        if new_value is None:
            self.set_line_null()
        else:
            for choice_key, label in self.choices:
                if choice_key == new_value:
                    self.field_value = new_value
                    self.setText(label)
                    self.set_line_normal()
                    return

            # Key not found
            self.set_line_null()

    def keyPressEvent(self, event):
        """Handle key events for dropdown interaction."""
        if event.key() == Qt.Key.Key_Down:
            if not self._dropdown.isVisible():
                # Show dropdown when down arrow is pressed
                self._show_dropdown()
            else:
                # Move to next item in dropdown
                current_row = self._dropdown.list_widget.currentRow()
                if current_row < self._dropdown.list_widget.count() - 1:
                    self._dropdown.list_widget.setCurrentRow(current_row + 1)
            return
        elif event.key() == Qt.Key.Key_Up:
            if self._dropdown.isVisible():
                # Move to previous item in dropdown
                current_row = self._dropdown.list_widget.currentRow()
                if current_row > 0:
                    self._dropdown.list_widget.setCurrentRow(current_row - 1)
            return
        elif (
            event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter
        ):
            if self._dropdown.isVisible():
                # Select current item
                current_item = self._dropdown.list_widget.currentItem()
                if current_item:
                    key = current_item.data(Qt.ItemDataRole.UserRole)
                    label = current_item.text()
                    self._on_item_selected(key, label)
                    self._dropdown.hide()
                    return
        elif event.key() == Qt.Key.Key_Escape and self._dropdown.isVisible():
            self._dropdown.hide()
            return

        super().keyPressEvent(event)

        # Refresh the dropdown filter after typing any other key
        # This ensures the dropdown shows the filtered choices
        if event.text() and self.choices:
            QTimer.singleShot(
                10,
                lambda: self._filter_choices(
                    self.text()
                ),  # type: ignore[arg-type]
            )

    def focusOutEvent(self, event):
        """Handle focus lost."""
        super().focusOutEvent(event)
        # Use timer to allow click events on dropdown to complete
        # QTimer.singleShot(100, self._check_focus_for_dropdown_hide)

    def focusInEvent(self, event):
        """Handle focus gained."""
        super().focusInEvent(event)
        # Show dropdown if it was visible before focus change
        if not self._dropdown.isVisible():
            self._on_text_changed(self.text())

    def _check_focus_for_dropdown_hide(self):
        """Check if dropdown should be hidden after focus change."""
        if (
            self._dropdown.isVisible()
            and not self._dropdown.hasFocus()
            and not self.hasFocus()
        ):
            self._dropdown.hide()


if __name__ == "__main__":
    import sys

    from PyQt5.QtWidgets import QApplication

    from exdrf_qt.context import QtContext as LocalContext

    app = QApplication(sys.argv)
    main_window = QWidget()
    main_window.setWindowTitle("DrfEnumEditor Example")

    ctx = LocalContext(c_string="sqlite:///:memory:")

    # Create a layout and add three DrfBlobEditor controls
    layout = QVBoxLayout()

    choices = [
        ("1", "Apple"),
        ("2", "Banana"),
        ("3", "Cherry"),
        ("4", "Dragon-fruit"),
        ("5", "Elderberry"),
        ("6", "Fig"),
        ("7", "Grapefruit"),
        ("8", "Honeydew"),
    ]
    line_edit_1 = DrfEnumEditor(
        choices=choices, ctx=ctx, nullable=True, description="Nullable choice"
    )
    line_edit_1.change_field_value(None)
    layout.addWidget(line_edit_1)

    line_edit_2 = DrfEnumEditor(
        choices=choices,
        ctx=ctx,
        nullable=False,
        description="Non-nullable choice",
    )
    line_edit_2.change_field_value(None)
    layout.addWidget(line_edit_2)

    line_edit_3 = DrfEnumEditor(
        choices=choices, ctx=ctx, nullable=True, description="With value"
    )
    line_edit_3.change_field_value("3")
    layout.addWidget(line_edit_3)

    main_window.setLayout(layout)
    main_window.show()
    sys.exit(app.exec_())
