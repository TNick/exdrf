import logging
from typing import TYPE_CHECKING, Any, Optional, cast

from exdrf.var_bag import VarBag
from PyQt5.QtCore import (
    QAbstractItemModel,
    QModelIndex,
    QObject,
    Qt,
    pyqtSignal,
)
from PyQt5.QtGui import QColor

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from exdrf.field import ExField

    from exdrf_qt.context import QtContext  # noqa: F401


logger = logging.getLogger(__name__)


class VarModel(QAbstractItemModel, QtUseContext):
    """Model for variables of a template.

    Attributes:
        name_filter: the filter applied to the name column;
        value_filter: the filter applied to the value column;
        var_bag: the unfiltered variables;
        filtered_bag: the filtered variables that are currently displayed.

    Signals:
        varDataChanged: emitted when underlying data changes.
    """

    name_filter: str
    value_filter: str
    _var_bag: "VarBag"
    filtered_bag: "VarBag"

    varDataChanged = pyqtSignal()

    def __init__(
        self,
        ctx: "QtContext",
        var_bag: "VarBag",
        parent: Optional["QObject"] = None,
    ):
        super().__init__(parent)
        self.ctx = ctx
        self._var_bag = var_bag if var_bag else VarBag()
        self.filtered_bag = self._var_bag
        self.name_filter = ""
        self.value_filter = ""

    @property
    def var_bag(self) -> "VarBag":
        """The variable bag of the template viewer."""
        return self._var_bag

    @var_bag.setter
    def var_bag(self, value: "VarBag"):
        """Set the variable bag of the template viewer."""
        self.beginResetModel()
        self._var_bag = value
        self.filtered_bag = self._var_bag
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()):
        if not parent.isValid():
            return len(self.filtered_bag.fields)

        # Items have no children.
        return 0

    def columnCount(self, parent: QModelIndex = QModelIndex()):
        return 2

    def hasChildren(self, parent: QModelIndex = QModelIndex()):
        if not parent.isValid():
            return True

        # Items have no children.
        return False

    def parent(self, child: QModelIndex = QModelIndex()):
        # Items have no children.
        return QModelIndex()

    def index(self, row: int, column: int, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if parent.isValid():
            return QModelIndex()

        return self.createIndex(row, column)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        row = index.row()
        column = index.column()
        field = self.filtered_bag.fields[row]
        value = self.filtered_bag[field.name]

        if role == Qt.ItemDataRole.DisplayRole:
            if column == 0:
                return field.name
            elif column == 1:
                if value is None:
                    return self.t("cmn.NULL", "NULL")
                return field.value_to_str(value)
        elif role == Qt.ItemDataRole.ToolTipRole:
            if column == 0:
                return field.description
            elif column == 1:
                return str(value)
        elif role == Qt.ItemDataRole.EditRole:
            if column == 1:
                return value
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if column == 0:
                return Qt.AlignmentFlag.AlignLeft
            elif column == 1:
                return Qt.AlignmentFlag.AlignRight
        elif role == Qt.ItemDataRole.ForegroundRole:
            if column == 0:
                return QColor("blue")
        return None

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = 0
    ):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                if section == 0:
                    return self.t("cmn.field", "Field")
                elif section == 1:
                    return self.t("cmn.value", "Value")
            elif orientation == Qt.Orientation.Vertical:
                return f"{section + 1}"
        return None

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        column = index.column()

        base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if column == 1:
            base |= Qt.ItemFlag.ItemIsEditable
        return cast(Qt.ItemFlags, base)

    def setData(
        self, index: QModelIndex, value: Any, role=Qt.ItemDataRole.EditRole
    ) -> bool:
        if not index.isValid():
            return False

        row = index.row()
        if index.column() != 1:
            return False

        field = self.filtered_bag.fields[row]
        old_value = self.filtered_bag[field.name]

        if role == Qt.ItemDataRole.EditRole:
            self._var_bag[field.name] = value
            self.filtered_bag[field.name] = value
            logger.info(
                "VarModel.setData: %s: %s -> %s",
                field.name,
                old_value,
                value,
            )
            self.varDataChanged.emit()
            return True
        return False

    def sort(
        self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder
    ) -> None:
        self.beginResetModel()
        try:
            if column == 0:
                self.filtered_bag.fields.sort(key=lambda x: x.name)
            else:
                self.filtered_bag.fields.sort(
                    key=lambda x: str(self.filtered_bag[x.name])
                )
        except Exception as e:
            logger.error("Error sorting model: %s", e, exc_info=True)
        self.endResetModel()

    def apply_filter(self, column: int, text: str, exact: bool):
        self.beginResetModel()
        try:
            self.filtered_bag = self._var_bag.filtered(
                by_name=column == 0, text=text, exact=exact
            )
            if column == 0:
                self.name_filter = text
            else:
                self.value_filter = text
        except Exception as e:
            logger.error("Error applying filter: %s", e, exc_info=True)
        self.endResetModel()

    def add_field(self, field: "ExField", value: Any = None):
        """Add a field to the bag.

        Args:
            field: The field to add.
            value: The value to add to the field.
        """
        self.beginResetModel()
        self._var_bag.add_field(field, value)
        if self._var_bag is not self.filtered_bag:
            self.filtered_bag.add_field(field, value)
        self.varDataChanged.emit()
        self.endResetModel()
