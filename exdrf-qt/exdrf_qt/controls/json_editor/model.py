import json
import logging
from typing import cast

from PyQt5 import QtCore, QtGui, QtWidgets

from exdrf_qt.controls.json_editor.item import JsonTreeItem

logger = logging.getLogger(__name__)


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
                logger.error(f"Invalid JSON string: {data}", exc_info=True)
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
