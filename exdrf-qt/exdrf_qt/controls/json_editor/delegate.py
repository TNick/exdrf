from typing import cast

from PyQt5 import QtCore, QtGui, QtWidgets

from exdrf_qt.controls.json_editor.model import JsonModel


class JsonDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        if index.column() == 0:
            return super().createEditor(parent, option, index)

        if index.column() != 1:
            return None

        item = index.internalPointer()
        if not item or item.type in ["dict", "list", "unknown", "null"]:
            return None

        model = cast(JsonModel, index.model())
        if item.path() in model._read_only_keys:
            return None

        if item.type == "string":
            editor = QtWidgets.QPlainTextEdit(parent)
            editor.setWordWrapMode(
                QtGui.QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere
            )
            editor.installEventFilter(self)
            return editor
        elif item.type == "integer":
            editor = QtWidgets.QSpinBox(parent)
            editor.setRange(-2147483648, 2147483647)
            return editor
        elif item.type == "float":
            editor = QtWidgets.QDoubleSpinBox(parent)
            editor.setRange(-1.79e308, 1.79e308)
            editor.setDecimals(15)
            return editor
        elif item.type == "boolean":
            editor = QtWidgets.QComboBox(parent)
            editor.addItems(["True", "False"])
            return editor

        return super().createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        if index.column() == 0:
            return super().setEditorData(editor, index)

        model = index.model()
        if not model:
            return
        value = model.data(index, QtCore.Qt.ItemDataRole.EditRole)
        item = index.internalPointer()
        if not item:
            return

        if item.type == "string":
            cast(QtWidgets.QPlainTextEdit, editor).setPlainText(str(value))
        elif item.type == "boolean":
            cast(QtWidgets.QComboBox, editor).setCurrentText(
                "True" if value else "False"
            )
        elif item.type == "float":
            cast(QtWidgets.QDoubleSpinBox, editor).setValue(float(value))
        elif item.type == "integer":
            cast(QtWidgets.QSpinBox, editor).setValue(int(value))
        else:
            super().setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        if index.column() == 0:
            return super().setModelData(editor, model, index)

        item = index.internalPointer()
        if not item:
            return

        value = None
        if item.type == "string":
            value = cast(QtWidgets.QPlainTextEdit, editor).toPlainText()
        elif item.type == "integer":
            cast(QtWidgets.QSpinBox, editor).interpretText()
            value = cast(QtWidgets.QSpinBox, editor).value()
        elif item.type == "float":
            cast(QtWidgets.QDoubleSpinBox, editor).interpretText()
            value = cast(QtWidgets.QDoubleSpinBox, editor).value()
        elif item.type == "boolean":
            value = cast(QtWidgets.QComboBox, editor).currentText() == "True"
        else:
            super().setModelData(editor, model, index)
            return

        if model:
            model.setData(index, value, QtCore.Qt.ItemDataRole.EditRole)

    def eventFilter(self, object, event):
        if not event:
            return super().eventFilter(object, event)
        if (
            isinstance(object, QtWidgets.QPlainTextEdit)
            and event.type() == QtCore.QEvent.Type.KeyPress
        ):
            key_event = cast(QtGui.QKeyEvent, event)
            if (
                key_event.key()
                in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter)
                and key_event.modifiers()
                == QtCore.Qt.KeyboardModifier.ControlModifier
            ):
                self.commitAndCloseEditor.emit()  # type: ignore
                return True
        return super().eventFilter(object, event)

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        if index.column() == 1:
            item = index.internalPointer()
            if item and item.type == "string":
                text = str(item.value)
                if "\n" in text:
                    fm = option.fontMetrics
                    size.setHeight(fm.height() * 4)
        return size

    def updateEditorGeometry(self, editor, option, index):
        if isinstance(editor, QtWidgets.QPlainTextEdit):
            rect = QtCore.QRect(option.rect)
            # Heuristic to make it bigger for editing
            rect.setHeight(max(option.rect.height() * 3, 70))
            editor.setGeometry(rect)
        else:
            super().updateEditorGeometry(editor, option, index)
