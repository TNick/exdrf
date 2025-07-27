import json
from typing import cast

import yaml
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices


class JsonTreeItem:
    def __init__(self, key, value=None, parent=None, add_to_parent=True):
        self._parent = parent
        self._key = key
        self._value = value
        self._children = []
        self._is_null = False

        if self._parent and add_to_parent:
            self._parent.add_child(self)

        self.load()

    def add_child(self, child):
        self._children.append(child)

    def insert_child(self, position, key, value):
        if position < 0 or position > len(self._children):
            return None

        item = JsonTreeItem(key, value, self, add_to_parent=False)
        self._children.insert(position, item)
        return item

    def remove_child(self, position):
        if position < 0 or position >= len(self._children):
            return
        self._children.pop(position)

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, key):
        self._key = key

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
        self._is_null = False
        # Clear existing children and reload
        self._children = []
        self.load()

    def set_to_null(self):
        self._value = None
        self._is_null = True
        self._children = []

    @property
    def is_null(self):
        return self._is_null

    @property
    def type(self):
        if self._is_null:
            return "null"
        if isinstance(self._value, bool):
            return "boolean"
        if isinstance(self._value, dict):
            return "dict"
        if isinstance(self._value, list):
            return "list"
        if isinstance(self._value, str):
            return "string"
        if isinstance(self._value, float):
            return "float"
        if isinstance(self._value, int):
            return "integer"
        return "unknown"

    def child(self, row):
        if 0 <= row < len(self._children):
            return self._children[row]
        return None

    def child_count(self):
        return len(self._children)

    def parent(self):
        return self._parent

    def row(self):
        if self._parent:
            return self._parent._children.index(self)
        return 0

    def load(self):
        if isinstance(self._value, dict):
            for key, value in self._value.items():
                JsonTreeItem(key, value, self)
        elif isinstance(self._value, list):
            for i, value in enumerate(self._value):
                JsonTreeItem(f"[{i}]", value, self)

    def to_python(self):
        if self.is_null:
            return None
        if self.type == "dict":
            return {child.key: child.to_python() for child in self._children}
        if self.type == "list":
            return [child.to_python() for child in self._children]
        return self.value

    def path(self, dot_notation=True) -> str | list[str]:
        path_parts = []
        current = self
        while current:
            parent: JsonTreeItem | None = current.parent()
            if parent is None:
                break
            if parent.type == "list":
                path_parts.append(str(current.row()))
            else:
                path_parts.append(current.key)

            current = current.parent()
            if current and not current.parent():  # Stop at root item's children
                break

        path_parts.reverse()
        if dot_notation:
            return ".".join(path_parts)
        return path_parts


class JsonModel(QtCore.QAbstractItemModel):
    def __init__(
        self,
        data=None,
        parent=None,
        nullable=False,
        read_only_keys=None,
        undeletable_keys=None,
    ):
        super().__init__(parent)
        self._root_item = JsonTreeItem("root", {})
        self._nullable = nullable
        self._read_only_keys = read_only_keys or []
        self._undeletable_keys = undeletable_keys or []

        if data:
            self.load(data)

    def load(self, data):
        self.beginResetModel()
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                data = {}  # Or handle error appropriately
        self._root_item = JsonTreeItem("root", data)
        self.endResetModel()

    def data(self, index, role=QtCore.Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        item = index.internalPointer()

        if role in (
            QtCore.Qt.ItemDataRole.DisplayRole,
            QtCore.Qt.ItemDataRole.EditRole,
        ):
            if index.column() == 0:
                return str(item.key)
            if index.column() == 1:
                if role == QtCore.Qt.ItemDataRole.EditRole:
                    return item.value
                if item.is_null:
                    return "NULL"
                if item.type in ["dict", "list"]:
                    return ""
                return str(item.value)
            return None

        if (
            role == QtCore.Qt.ItemDataRole.DecorationRole
            and index.column() == 0
        ):
            style = QtWidgets.QApplication.style()
            assert style is not None, "Style is not set"
            if item.type == "dict":
                return style.standardIcon(
                    QtWidgets.QStyle.StandardPixmap.SP_DirIcon
                )
            if item.type == "list":
                return style.standardIcon(
                    QtWidgets.QStyle.StandardPixmap.SP_FileDialogDetailedView
                )

        if role == QtCore.Qt.ItemDataRole.BackgroundRole:
            path = item.path()
            if path in self._read_only_keys:
                color = QtGui.QColor(230, 230, 230)  # light grey
                if index.column() == 1:
                    color = QtGui.QColor(240, 240, 220)  # light yellow
                return color

        if role == QtCore.Qt.ItemDataRole.ForegroundRole:
            if item.is_null and index.column() == 1:
                return QtGui.QColor("grey")

        return None

    def setData(self, index, value, role=QtCore.Qt.ItemDataRole.EditRole):
        if not index.isValid() or role != QtCore.Qt.ItemDataRole.EditRole:
            return False

        item = index.internalPointer()
        path = item.path()

        if path in self._read_only_keys:
            return False

        if index.column() == 0:  # Key
            if path in self._undeletable_keys:
                return False  # Cannot rename

            parent_item = item.parent()
            if parent_item and parent_item.type == "dict":
                # Check for duplicate keys
                if any(
                    child.key == value
                    for child in parent_item._children
                    if child is not item
                ):
                    return False
                item.key = value
                self.dataChanged.emit(
                    index, index, [QtCore.Qt.ItemDataRole.EditRole]
                )
                return True
            return False  # Cannot change index of a list item

        if index.column() == 1:  # Value
            current_type = item.type
            new_value = value

            # Try to convert to a more specific type
            # try:
            #     new_value = int(value)
            # except (ValueError, TypeError):
            #     try:
            #         new_value = float(value)
            #     except (ValueError, TypeError):
            #         if value.lower() == "true":
            #             new_value = True
            #         elif value.lower() == "false":
            #             new_value = False

            old_value = item.value
            item.value = new_value
            self.dataChanged.emit(
                index, index, [QtCore.Qt.ItemDataRole.EditRole]
            )
            # If the type changed (e.g. from string to dict),
            # we might need to refresh children
            type_changed = item.type != current_type
            multiline_changed = (
                item.type == "string"
                and isinstance(old_value, str)
                and isinstance(new_value, str)
                and (("\n" in old_value) != ("\n" in new_value))
            )
            if type_changed or multiline_changed:
                self.layoutChanged.emit()
            return True

        return False

    def headerData(
        self, section, orientation, role=QtCore.Qt.ItemDataRole.DisplayRole
    ):
        if (
            orientation == QtCore.Qt.Orientation.Horizontal
            and role == QtCore.Qt.ItemDataRole.DisplayRole
        ):
            if section == 0:
                return "Key"
            if section == 1:
                return "Value"
        return None

    def index(self, row, column, parent=QtCore.QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()

        parent_item = (
            parent.internalPointer() if parent.isValid() else self._root_item
        )
        child_item = parent_item.child(row)

        if child_item:
            return self.createIndex(row, column, child_item)
        return QtCore.QModelIndex()

    def parent(  # type: ignore
        self, index: QtCore.QModelIndex
    ) -> QtCore.QModelIndex:
        if not index.isValid():
            return QtCore.QModelIndex()

        child_item = index.internalPointer()
        parent_item = child_item.parent()

        if parent_item == self._root_item:
            return QtCore.QModelIndex()

        if parent_item:
            return self.createIndex(parent_item.row(), 0, parent_item)
        return QtCore.QModelIndex()

    def rowCount(self, parent=QtCore.QModelIndex()):
        parent_item = (
            parent.internalPointer() if parent.isValid() else self._root_item
        )
        return parent_item.child_count()

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 2

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlags:
        if not index.isValid():
            return cast(QtCore.Qt.ItemFlags, QtCore.Qt.ItemFlag.NoItemFlags)

        flags = (
            QtCore.Qt.ItemFlag.ItemIsEnabled
            | QtCore.Qt.ItemFlag.ItemIsSelectable
        )
        item = index.internalPointer()
        path = item.path()

        if path in self._read_only_keys:
            return cast(QtCore.Qt.ItemFlags, flags)

        # Key editing
        if (
            item.parent()
            and item.parent().type == "dict"
            and index.column() == 0
        ):
            if path not in self._undeletable_keys:
                flags |= QtCore.Qt.ItemFlag.ItemIsEditable

        # Value editing
        if index.column() == 1 and item.type not in ["dict", "list"]:
            flags |= QtCore.Qt.ItemFlag.ItemIsEditable

        return cast(QtCore.Qt.ItemFlags, flags)

    def to_python(self):
        return self._root_item.to_python()

    def _get_new_key(self, parent_item):
        if parent_item.type == "dict":
            base_key = "new_key"
            key = base_key
            i = 1
            existing_keys = {child.key for child in parent_item._children}
            while key in existing_keys:
                key = f"{base_key}_{i}"
                i += 1
            return key
        elif parent_item.type == "list":
            return f"[{parent_item.child_count()}]"
        return ""

    def add_item(self, parent_index, item_type):
        parent_item = (
            parent_index.internalPointer()
            if parent_index.isValid()
            else self._root_item
        )

        if parent_item.type not in ["dict", "list"]:
            return False

        position = parent_item.child_count()
        self.beginInsertRows(parent_index, position, position)

        key = self._get_new_key(parent_item)
        value = None
        if item_type == "dict":
            value = {}
        elif item_type == "list":
            value = []
        elif item_type == "string":
            value = ""
        elif item_type == "integer":
            value = 0
        elif item_type == "float":
            value = 0.0
        elif item_type == "boolean":
            value = False

        parent_item.insert_child(position, key, value)

        self.endInsertRows()
        return True

    def remove_items(self, indexes):
        # Group indexes by parent
        parent_map = {}
        for index in sorted(indexes, key=lambda idx: idx.row(), reverse=True):
            parent_index = index.parent()
            if parent_index not in parent_map:
                parent_map[parent_index] = []
            parent_map[parent_index].append(index)

        for parent_index, child_indexes in parent_map.items():
            parent_item = (
                parent_index.internalPointer()
                if parent_index.isValid()
                else self._root_item
            )

            for index in child_indexes:
                item_to_remove = index.internalPointer()
                path = item_to_remove.path()

                if (
                    path in self._read_only_keys
                    or path in self._undeletable_keys
                ):
                    continue

                row = index.row()
                self.beginRemoveRows(parent_index, row, row)
                parent_item.remove_child(row)
                self.endRemoveRows()

        # After removal, list indices might need updating
        self.layoutChanged.emit()


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


class JsonTreeView(QtWidgets.QTreeView):
    edit_as_text_requested = QtCore.pyqtSignal()

    def __init__(
        self,
        data=None,
        nullable=False,
        read_only_keys=None,
        undeletable_keys=None,
        parent=None,
    ):
        super().__init__(parent)
        self.setSelectionMode(self.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.setRootIsDecorated(True)
        self.setHeaderHidden(False)

        self._model = JsonModel(
            data, self, nullable, read_only_keys, undeletable_keys
        )
        self.setModel(self._model)
        self.setItemDelegate(JsonDelegate(self))
        self.expandAll()

        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def to_python(self):
        return self._model.to_python()

    def to_yaml(self, selection=False):
        data_to_dump = self.to_python()
        if selection:
            s_model = self.selectionModel()
            assert s_model is not None, "Selection model is not set"
            selected_indexes = s_model.selectedIndexes()
            if selected_indexes:
                # This is a simplification. For multiple selection, we'd need
                # to construct a proper structure. For now, we handle the first
                # selected item's subtree.
                root_item = selected_indexes[0].internalPointer()
                data_to_dump = root_item.to_python()

        return yaml.dump(data_to_dump, allow_unicode=True)

    def keyPressEvent(self, event):
        if event and event.matches(QtGui.QKeySequence.Copy):
            self.copy_selection_to_clipboard()
        else:
            super().keyPressEvent(event)

    def copy_selection_to_clipboard(self):
        yaml_str = self.to_yaml(selection=True)
        clipboard = QtWidgets.QApplication.clipboard()
        assert clipboard is not None, "Clipboard is not set"
        clipboard.setText(yaml_str)

    def _show_context_menu(self, pos):
        menu = QtWidgets.QMenu(self)

        s_model = self.selectionModel()
        assert s_model is not None, "Selection model is not set"
        indexes = s_model.selectedIndexes()
        index = self.indexAt(pos)
        item = index.internalPointer()

        add_menu = menu.addMenu("Add")
        assert add_menu is not None, "Add menu is not set"

        can_add = False
        if not index.isValid():  # right click on empty space
            can_add = True
        elif item and item.type in ["dict", "list"]:
            can_add = True

        if can_add:
            add_menu.addAction(
                "Dictionary", lambda: self._model.add_item(index, "dict")
            )
            add_menu.addAction(
                "List", lambda: self._model.add_item(index, "list")
            )
            add_menu.addAction(
                "String", lambda: self._model.add_item(index, "string")
            )
            add_menu.addAction(
                "Integer", lambda: self._model.add_item(index, "integer")
            )
            add_menu.addAction(
                "Float", lambda: self._model.add_item(index, "float")
            )
            add_menu.addAction(
                "Boolean", lambda: self._model.add_item(index, "boolean")
            )
        else:
            add_menu.setDisabled(True)

        if indexes:
            menu.addAction("Remove", self._remove_selected)

        if self._model._nullable:
            menu.addAction("Set to NULL", self._set_to_null)

        menu.addSeparator()
        menu.addAction("Expand All Children", self.expandAll)
        menu.addAction("Collapse All Children", self.collapseAll)
        menu.addSeparator()

        io_menu = menu.addMenu("I/O")
        assert io_menu is not None, "I/O menu is not set"
        io_menu.addAction("Copy as YAML", self.copy_selection_to_clipboard)
        io_menu.addAction("Edit as text", self.edit_as_text_requested.emit)

        load_menu = io_menu.addMenu("Load from")
        assert load_menu is not None, "Load menu is not set"
        load_menu.addAction("JSON...", lambda: self._load_from_file("json"))
        load_menu.addAction("YAML...", lambda: self._load_from_file("yaml"))

        save_menu = io_menu.addMenu("Save to")
        assert save_menu is not None, "Save menu is not set"
        save_menu.addAction("JSON...", lambda: self._save_to_file("json"))
        save_menu.addAction("YAML...", lambda: self._save_to_file("yaml"))

        vp = self.viewport()
        assert vp is not None, "Viewport is not set"
        menu.exec(vp.mapToGlobal(pos))

    def _remove_selected(self):
        s_model = self.selectionModel()
        assert s_model is not None, "Selection model is not set"
        indexes = s_model.selectedIndexes()
        if not indexes:
            return
        # Filter for column 0 to avoid processing the same row multiple times
        indexes_col0 = [idx for idx in indexes if idx.column() == 0]
        self._model.remove_items(indexes_col0)

    def _set_to_null(self):
        index = self.currentIndex()
        if not index.isValid():
            return
        item = index.internalPointer()
        item.set_to_null()
        self._model.dataChanged.emit(index, index)
        self._model.layoutChanged.emit()

    def _load_from_file(self, file_type):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            f"Load {file_type.upper()}",
            "",
            f"{file_type.upper()} Files (*.{file_type});;All Files (*)",
        )
        if not path:
            return

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            if file_type == "json":
                data = json.loads(content)
            elif file_type == "yaml":
                data = yaml.safe_load(content)
            else:
                return
            self._model.load(data)
            self.expandAll()

    def _save_to_file(self, file_type):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            f"Save {file_type.upper()}",
            "",
            f"{file_type.upper()} Files (*.{file_type});;All Files (*)",
        )
        if not path:
            return

        data = self.to_python()
        with open(path, "w", encoding="utf-8") as f:
            if file_type == "json":
                json.dump(data, f, indent=4)
            elif file_type == "yaml":
                yaml.dump(data, f, allow_unicode=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))


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


class JsonEditorDialog(QtWidgets.QDialog):
    def __init__(
        self,
        data=None,
        nullable=False,
        read_only_keys=None,
        undeletable_keys=None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("JSON Editor")

        self.editor = JsonEditor(
            data, nullable, read_only_keys, undeletable_keys
        )

        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.editor)
        layout.addWidget(self.button_box)

        self.resize(600, 500)

    def get_data(self):
        return self.editor.to_python()

    @staticmethod
    def edit_json(
        data,
        nullable=False,
        read_only_keys=None,
        undeletable_keys=None,
        parent=None,
    ):
        dialog = JsonEditorDialog(
            data, nullable, read_only_keys, undeletable_keys, parent
        )
        result = dialog.exec()
        if result == QtWidgets.QDialog.Accepted:
            return True, dialog.get_data()
        return False, None


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)

    # Example usage
    initial_data = {
        "name": "John Doe",
        "age": 30,
        "isStudent": False,
        "courses": [
            {"title": "History", "credits": 3},
            {"title": "Math", "credits": 4},
        ],
        "address": {"street": "123 Main St", "city": "Anytown"},
        "metadata": None,
    }

    read_only = ["address.city"]
    undeletable = ["name"]

    ok, new_data = JsonEditorDialog.edit_json(
        initial_data,
        nullable=True,
        read_only_keys=read_only,
        undeletable_keys=undeletable,
    )

    if ok:
        print("Editing successful:")
        print(json.dumps(new_data, indent=2))
    else:
        print("Editing cancelled.")

    sys.exit(app.exec())
