import json

import yaml
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices

from exdrf_qt.controls.json_editor.delegate import JsonDelegate
from exdrf_qt.controls.json_editor.model import JsonModel


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
