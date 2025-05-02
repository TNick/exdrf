from PyQt5.QtWidgets import QAction, QLineEdit

from exdrf_qt.field_ed.base import DrfFieldEd


class LineBase(QLineEdit, DrfFieldEd):
    """Base for classes that are based on line edit controls."""

    clear_ac: QAction

    def set_line_empty(self):
        """Changes the aspect of the line edit to indicate that it is null."""
        if self.nullable:
            self.setStyleSheet(
                "QLineEdit { color: gray; font-style: italic; } "
            )
            self.setPlaceholderText(self.t("cmn.NULL", "NULL"))
        else:
            self.setStyleSheet("QLineEdit { color: red; font-style: italic; } ")
            self.setPlaceholderText(self.t("cmn.Empty", "Empty"))

            error = self.t("cmn.err.field_is_empty", "Field cannot be empty")
            self.enteredErrorState.emit(error)
            self.setToolTip(error)
        self.setText("")

    def set_line_normal(self):
        """Changes the aspect of the line edit to indicate that the control has
        a valid value.
        """
        self.setStyleSheet("QLineEdit { color: black; font-style: normal; } ")
        self.setPlaceholderText("")
        self.setToolTip(self.description if self.description else "")

    def set_line_error(self, error: str):
        """Changes the aspect of the line edit to indicate that the control
        is in an error state.
        """
        self.setStyleSheet("QLineEdit { color: red; font-style: normal; } ")
        self.setPlaceholderText(self.t("cmn.ERROR", "ERROR"))
        self.enteredErrorState.emit(error)
        self.setToolTip(error)

    def add_clear_to_null_action(self):
        """Adds a clear to null action to the line edit."""
        self.clear_ac = QAction(
            self.get_icon("clear_to_null"),
            self.t("cmn.clear_to_null", "Clear to NULL"),
            self,
        )
        self.clear_ac.triggered.connect(self.set_line_null)
        self.addAction(self.clear_ac, QLineEdit.ActionPosition.LeadingPosition)

    def set_line_null(self):
        """Sets the line edit to null."""
        raise NotImplementedError(
            "set_line_null() must be implemented in subclasses."
        )
