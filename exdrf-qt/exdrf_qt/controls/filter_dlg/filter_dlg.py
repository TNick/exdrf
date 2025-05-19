from typing import TYPE_CHECKING, Generic, Union

from exdrf.filter import FilterType
from exdrf.filter_dsl import FieldValidator
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QDialog, QDialogButtonBox

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.filter_dlg.filter_dlg_ui import Ui_FilterDlg
from exdrf_qt.models.model import DBM, QtModel  # noqa: F401

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401


class FilterDlg(QDialog, Ui_FilterDlg, QtUseContext, Generic[DBM]):
    """A dialog that allows the user to create a filter."""

    def __init__(self, ctx: "QtContext", qt_model: "QtModel[DBM]", **kwargs):
        """Initialize the editor widget."""
        super().__init__(**kwargs)
        self.ctx = ctx
        self.qt_model = qt_model
        self.setup_ui(self)

        self.c_text.prepare(
            validator=FieldValidator(
                ctx=self.ctx,
                qt_model=self.qt_model,
            ),
            l_error=self.l_error,
            qt_model=self.qt_model,
        )
        self.c_text.errorChanged.connect(self._on_error_changed)

        btn_apply = self.bbox.button(QDialogButtonBox.StandardButton.Apply)
        assert btn_apply is not None
        btn_apply.clicked.connect(self.accept)

        # Create the AND button.
        self.btn_and = self.bbox.addButton(
            self.t("cmn.and", "AND"), QDialogButtonBox.ButtonRole.ActionRole
        )
        assert self.btn_and is not None
        self.btn_and.clicked.connect(self._on_and_clicked)

        # Create the OR button.
        self.btn_or = self.bbox.addButton(
            self.t("cmn.or", "OR"), QDialogButtonBox.ButtonRole.ActionRole
        )
        assert self.btn_or is not None
        self.btn_or.clicked.connect(self._on_or_clicked)

    @property
    def filter(self) -> Union[FilterType, None]:
        """Return the filter as a dictionary."""
        return self.c_text.filter

    def _insert_logical_block(self, operator: str) -> None:
        """Insert a logical block (AND/OR) and position cursor.

        Args:
            operator: The logical operator to insert ("AND" or "OR")
        """
        cursor = self.c_text.textCursor()

        if cursor.hasSelection():
            # Get selected text
            selected_text = cursor.selectedText()
            # Split it in lines and add a tab before each line
            selected_text = "\n".join(
                [f"\t{line}" for line in selected_text.split("\n")]
            )
            # Replace selection with operator block containing selection
            cursor.insertText(f"{operator} (\n{selected_text}\n)")
        else:
            # Insert empty operator block
            cursor.insertText(f"{operator} (\n\n)")

        # Move cursor between parentheses
        cursor.movePosition(QTextCursor.Up)
        cursor.movePosition(QTextCursor.EndOfLine)

        # Set cursor and focus
        self.c_text.setTextCursor(cursor)
        self.c_text.setFocus()

    def _on_and_clicked(self):
        """Handle the AND button click."""
        self._insert_logical_block("AND")

    def _on_or_clicked(self):
        """Handle the OR button click."""
        self._insert_logical_block("OR")

    def _on_error_changed(self, has_error: bool):
        """Handle the error changed signal.

        Args:
            has_error: Whether there is an error in the filter.
        """
        btn_apply = self.bbox.button(QDialogButtonBox.StandardButton.Apply)
        assert btn_apply is not None
        btn_apply.setEnabled(not has_error)
