from typing import TYPE_CHECKING, List, Tuple, cast

from PyQt5.QtCore import Qt, pyqtProperty  # type: ignore
from PyQt5.QtWidgets import QCompleter

if TYPE_CHECKING:
    from exdrf_qt.field_ed.base_line import LineBase


class EditorWithChoices:
    _choices: List[Tuple[str, str]]

    def getChoices(self) -> str:
        """Get the valid choices.

        This is a support function for implementing the choices property.
        """
        return ",".join([f"{key}:{label}" for key, label in self._choices])

    def setChoices(self, value: str) -> None:
        """Set the valid choices.

        This is a support function for implementing the choices property.

        Args:
            value: a comma-separated list of key:label pairs.
        """
        if isinstance(value, str):
            self.set_choices(
                [
                    a.split(":", maxsplit=1)  # type: ignore
                    for a in value.split(",")
                ]
            )
        else:
            self.set_choices(value)

    choices = pyqtProperty(str, fget=getChoices, fset=setChoices)

    def set_choices(self, choices: List[Tuple[str, str]]):
        """Set the available choices."""
        self._choices = choices

        line = cast("LineBase", self)
        # Set the QLineEdit's auto-completer based on the list of choices

        # Extract the labels from the choices for autocompletion
        crt_completer = line.completer()
        if crt_completer is not None:
            crt_completer.deleteLater()

        labels = [label for _, label in choices]
        completer = QCompleter(labels, line)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        line.setCompleter(completer)

    def get_choices_value(self, text: str) -> str:
        """Replace text that is in the choices with the true value."""
        if not hasattr(self, "_choices") or self._choices is None:
            return text
        l_text = text.lower().strip()
        for key, label in self._choices:
            if label.lower() == l_text:
                return key
        return text

    def get_choices_label(self, text: str) -> str:
        """Replace text that is in the choices with the true label."""
        if not hasattr(self, "_choices") or self._choices is None:
            return text
        l_text = text.lower().strip()
        for key, label in self._choices:
            if str(key).lower() == l_text:
                return label
        return text
