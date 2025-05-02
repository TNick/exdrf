from PyQt5.QtWidgets import QAction, QLineEdit

from exdrf_qt.field_ed.base import DrfFieldEd


class LineBase(QLineEdit, DrfFieldEd):
    """Base for classes that are based on line edit controls."""

    ac_clear: QAction

    def set_line_empty(self):
        """Changes the aspect of the line edit to indicate that it is null.

        The control also issues a signal:
        - controlChanged: if NULL is an acceptable value for the field.
        - enteredErrorState: if NULL is not an acceptable value for the field.
        """
        self.setText("")
        if self.nullable:
            self.setStyleSheet(
                "QLineEdit { color: gray; font-style: italic; } "
            )
            self.setPlaceholderText(self.t("cmn.NULL", "NULL"))
            self.controlChanged.emit()
        else:
            self.setStyleSheet("QLineEdit { color: red; font-style: italic; } ")
            self.setPlaceholderText(self.t("cmn.Empty", "Empty"))

            error = self.null_error()
            self.setToolTip(error)
            self.enteredErrorState.emit(error)

    def set_line_normal(self):
        """Changes the aspect of the line edit to indicate that the control has
        a valid value.

        Note that this method does not emit any signal.
        """
        self.setStyleSheet("QLineEdit { color: black; font-style: normal; } ")
        self.setPlaceholderText("")
        self.setToolTip(self.description if self.description else "")

    def set_line_error(self, error: str):
        """Changes the aspect of the line edit to indicate that the control
        is in an error state.

        The control also issues the error signal.
        """
        self.setStyleSheet("QLineEdit { color: red; font-style: normal; } ")
        self.setPlaceholderText(self.t("cmn.ERROR", "ERROR"))
        self.setToolTip(error)
        self.enteredErrorState.emit(error)

    def add_clear_to_null_action(self):
        """Adds a clear to null action to the line edit."""
        self.ac_clear = QAction(
            self.get_icon("clear_to_null"),
            self.t("cmn.clear_to_null", "Clear to NULL"),
            self,
        )
        self.ac_clear.triggered.connect(self.set_line_null)
        self.addAction(self.ac_clear, QLineEdit.ActionPosition.LeadingPosition)

    def set_line_null(self):
        """Sets the line edit to null."""
        raise NotImplementedError(
            "set_line_null() must be implemented in subclasses."
        )
