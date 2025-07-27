import json
from typing import cast

import yaml
from PyQt5 import QtCore, QtGui, QtWidgets

from exdrf_qt.controls.json_editor.tree import JsonTreeView


class JsonEditor(QtWidgets.QWidget):
    def __init__(
        self,
        data=None,
        nullable=False,
        read_only_keys=None,
        undeletable_keys=None,
        parent=None,
    ):
        super().__init__(parent)

        self._tree_view = JsonTreeView(
            data, nullable, read_only_keys, undeletable_keys, self
        )
        self._text_editor = QtWidgets.QTextEdit(self)
        self._text_editor.setVisible(False)
        self._text_editor.installEventFilter(self)

        font = QtGui.QFont()
        font.setFamily("Courier New")
        font.setStyleHint(QtGui.QFont.StyleHint.Monospace)
        self._text_editor.setFont(font)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._tree_view)
        layout.addWidget(self._text_editor)

        self._tree_view.edit_as_text_requested.connect(self._show_text_editor)
        self._text_editor.textChanged.connect(self._on_text_changed)

    def eventFilter(  # type: ignore
        self, source: QtCore.QObject | None, event: QtCore.QEvent | None
    ) -> bool:  # type: ignore
        if event and source is self._text_editor:
            if event.type() == QtCore.QEvent.Type.KeyPress:
                key_event = cast(QtGui.QKeyEvent, event)
                if key_event.key() == QtCore.Qt.Key.Key_Escape:
                    self._hide_text_editor(save=False)
                    return True
                if (
                    key_event.key()
                    in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter)
                    and key_event.modifiers()
                    == QtCore.Qt.KeyboardModifier.ControlModifier
                ):
                    self._hide_text_editor(save=True)
                    return True
            elif event.type() == QtCore.QEvent.Type.FocusOut:
                self._hide_text_editor(save=True)
                return True

        return super().eventFilter(source, event)

    def _show_text_editor(self):
        data = self.to_python()
        try:
            text = yaml.dump(data, allow_unicode=True, sort_keys=False)
        except Exception:
            text = json.dumps(data, indent=2)

        self._text_editor.setText(text)
        self._text_editor.setVisible(True)
        self._text_editor.setFocus()

    def _hide_text_editor(self, save):
        if save:
            text = self._text_editor.toPlainText()
            try:
                data = yaml.safe_load(text)
                self._tree_view._model.load(data)
                self._tree_view.expandAll()
            except (yaml.YAMLError, json.JSONDecodeError):
                pass  # Invalid text, don't save

        self._text_editor.setVisible(False)

    def _on_text_changed(self):
        text = self._text_editor.toPlainText()
        try:
            data = yaml.safe_load(text)
            self._tree_view._model.load(data)
            self._tree_view.expandAll()
            self._text_editor.setStyleSheet("")
        except (yaml.YAMLError, json.JSONDecodeError):
            self._text_editor.setStyleSheet("background-color: #ffcccc;")

    def to_python(self):
        return self._tree_view.to_python()

    def to_yaml(self, selection=False):
        return self._tree_view.to_yaml(selection)
