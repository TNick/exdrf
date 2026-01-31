"""Qt model for template viewer variables (name/value table).

This module provides a QAbstractItemModel that backs a flat table of
template variables from a VarBag. It supports filtering by name or value,
sorting, editing the value column, and extra context (e.g. per-row
background color). Used by TemplViewer for the variables side panel.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional, cast

from exdrf.var_bag import VarBag
from PyQt5.QtCore import (
    QAbstractItemModel,
    QModelIndex,
    QObject,
    Qt,
    pyqtSignal,
)
from PyQt5.QtGui import QBrush, QColor
from typing_extensions import List

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from exdrf.field import ExField

    from exdrf_qt.context import QtContext  # noqa: F401


logger = logging.getLogger(__name__)


class VarModel(QAbstractItemModel, QtUseContext):
    """Qt item model for a flat table of template variables from a VarBag.

    Exposes two columns: name (field name) and value (current value).
    Supports filtering by name or value, sorting by either column, and
    editing the value column. extra_context can hold per-field overrides
    (e.g. background color for display). filtered_bag is the subset
    after apply_filter; var_bag is the full bag.

    Attributes:
        name_filter: Last filter text applied to the name column.
        value_filter: Last filter text applied to the value column.
        _var_bag: Full variable bag (backing store).
        filtered_bag: Currently displayed bag (var_bag or filtered subset).
        extra_context: Per-field extra data (e.g. bgcolor for display).

    Signals:
        varDataChanged: Emitted when variable data is changed (e.g. setData,
            add_field).
    """

    name_filter: str
    value_filter: str
    _var_bag: "VarBag"
    filtered_bag: "VarBag"
    extra_context: Dict[str, Any]

    varDataChanged = pyqtSignal()

    def __init__(
        self,
        ctx: "QtContext",
        var_bag: "VarBag",
        parent: Optional["QObject"] = None,
    ) -> None:
        """Initialize the model with context and variable bag.

        Args:
            ctx: Qt context for translation and settings.
            var_bag: Variable bag to display; if None, an empty VarBag is used.
            parent: Optional parent QObject for ownership.
        """
        super().__init__(parent)
        self.ctx = ctx
        self._var_bag = var_bag if var_bag else VarBag()
        self.filtered_bag = self._var_bag
        self.name_filter = ""
        self.value_filter = ""
        self.extra_context = {}

    @property
    def var_bag(self) -> "VarBag":
        """Return the full variable bag (unfiltered)."""
        return self._var_bag

    @var_bag.setter
    def var_bag(self, value: "VarBag") -> None:
        """Replace the variable bag; clear filters and extra context.

        Args:
            value: New variable bag to use.
        """
        self.beginResetModel()
        self._var_bag = value
        self.filtered_bag = self._var_bag
        self.extra_context = {}
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of rows (variable count) when parent is invalid.

        Args:
            parent: Parent index; only invalid (root) is supported.

        Returns:
            Number of fields in filtered_bag at root, else 0.
        """
        if not parent.isValid():
            return len(self.filtered_bag.fields)
        return 0

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of columns (always 2: name, value).

        Args:
            parent: Parent index (unused).

        Returns:
            2.
        """
        return 2

    def hasChildren(self, parent: QModelIndex = QModelIndex()) -> bool:
        """Return whether the parent has children (only root has rows).

        Args:
            parent: Parent index.

        Returns:
            True if parent is invalid (root), else False.
        """
        if not parent.isValid():
            return True
        return False

    def parent(self, child: QModelIndex = QModelIndex()) -> QModelIndex:
        """Return the parent of the given index (always invalid for flat model).

        Args:
            child: Child index (unused).

        Returns:
            Invalid index (no parent).
        """
        return QModelIndex()

    def index(
        self, row: int, column: int, parent: QModelIndex = QModelIndex()
    ) -> QModelIndex:
        """Return the model index for the given row and column at root.

        Args:
            row: Row index (field index).
            column: Column index (0 = name, 1 = value).
            parent: Parent index; must be invalid for a valid result.

        Returns:
            Valid index for (row, column) at root, or invalid index.
        """
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        if parent.isValid():
            return QModelIndex()
        return self.createIndex(row, column)

    def data(
        self,
        index: QModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Return data for the given index and role.

        DisplayRole: name or value (value as string via field.value_to_str).
        ToolTipRole: field description or str(value). EditRole: raw value
        for column 1. TextAlignmentRole: left for name, right for value.
        ForegroundRole: blue for name. BackgroundRole: from extra_context
        if set (str, QColor, or QBrush).

        Args:
            index: Model index (row = field index, column = 0 or 1).
            role: Qt item data role.

        Returns:
            Data for the role, or None.
        """
        if not index.isValid():
            return None

        row = index.row()
        column = index.column()
        field = self.filtered_bag.fields[row]
        value = self.filtered_bag[field.name]

        if role == Qt.ItemDataRole.DisplayRole:
            if column == 0:
                return field.name
            if column == 1:
                if value is None:
                    return self.t("cmn.NULL", "NULL")
                return field.value_to_str(value)
        elif role == Qt.ItemDataRole.ToolTipRole:
            if column == 0:
                return field.description
            if column == 1:
                return str(value)
        elif role == Qt.ItemDataRole.EditRole:
            if column == 1:
                return value
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if column == 0:
                return Qt.AlignmentFlag.AlignLeft
            if column == 1:
                return Qt.AlignmentFlag.AlignRight
        elif role == Qt.ItemDataRole.ForegroundRole:
            if column == 0:
                return QColor("blue")
        elif role == Qt.ItemDataRole.BackgroundRole:
            override = self.extra_context.get(field.name, None)
            if override:
                if isinstance(override, str):
                    return QBrush(QColor(override))
                if isinstance(override, QColor):
                    return QBrush(override)
                if isinstance(override, QBrush):
                    return override
        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Return header data for the given section and orientation.

        Horizontal: "Field" for column 0, "Value" for column 1. Vertical:
        row number (1-based) as string.

        Args:
            section: Section index (column or row).
            orientation: Horizontal or vertical.
            role: Qt item data role (only DisplayRole is handled).

        Returns:
            Header string or None.
        """
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                if section == 0:
                    return self.t("cmn.field", "Field")
                if section == 1:
                    return self.t("cmn.value", "Value")
            elif orientation == Qt.Orientation.Vertical:
                return f"{section + 1}"
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Return item flags (enabled, selectable; value column editable).

        Args:
            index: Model index.

        Returns:
            NoItemFlags if invalid; else ItemIsEnabled | ItemIsSelectable,
            and ItemIsEditable for column 1.
        """
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        column = index.column()
        base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if column == 1:
            base |= Qt.ItemFlag.ItemIsEditable
        return cast(Qt.ItemFlags, base)

    def setData(
        self,
        index: QModelIndex,
        value: Any,
        role: int = Qt.ItemDataRole.EditRole,
    ) -> bool:
        """Set data for the given index (value column only, EditRole).

        Updates both _var_bag and filtered_bag, logs the change, and
        emits varDataChanged.

        Args:
            index: Model index (must be column 1).
            value: New value to set.
            role: Qt item data role (only EditRole is handled).

        Returns:
            True if the value was set, else False.
        """
        if not index.isValid():
            return False
        if index.column() != 1:
            return False

        row = index.row()
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
        self,
        column: int,
        order: Qt.SortOrder = Qt.SortOrder.AscendingOrder,
    ) -> None:
        """Sort filtered_bag.fields by the given column (name or value string).

        Args:
            column: 0 to sort by name, 1 by value (string).
            order: Ascending or descending (currently only ascending key
                is applied; order is not inverted).
        """
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

    def apply_filter(self, column: int, text: str, exact: bool) -> None:
        """Filter the displayed bag by name or value and update filters.

        Replaces filtered_bag with the result of VarBag.filtered and
        updates name_filter or value_filter accordingly.

        Args:
            column: 0 to filter by name, 1 by value.
            text: Filter text.
            exact: Whether to require exact match.
        """
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

    def add_field(self, field: "ExField", value: Any = None) -> None:
        """Add a field to the bag and reset the model.

        If filtered_bag is not the same as _var_bag, also adds the field
        to filtered_bag. Emits varDataChanged.

        Args:
            field: Field to add.
            value: Optional initial value for the field.
        """
        self.beginResetModel()
        self._var_bag.add_field(field, value)
        if self._var_bag is not self.filtered_bag:
            self.filtered_bag.add_field(field, value)
        self.varDataChanged.emit()
        self.endResetModel()

    def from_simple_data(self, data: Any) -> None:
        """Load extra context (e.g. bgcolor) from a list of simple dicts.

        Iterates over data, resolves each item via var_bag.simple_to_one,
        and sets extra_context[field.name] to item["bgcolor"] when present.
        Does not replace var_bag values.

        Args:
            data: List of simple dicts (e.g. from to_simple_data).
        """
        for item in data:
            field, value = self.var_bag.simple_to_one(item)
            if field is None:
                continue
            color = item.get("bgcolor", None)
            if color:
                self.extra_context[field.name] = color

    def to_simple_data(self) -> List[Dict[str, Any]]:
        """Convert the variable bag to a list of simple dicts.

        Each dict has name, type, value; may include "bgcolor" from
        extra_context. Values are
        simple types (int, float, bool, str, list, dict); other types
        are converted to a string with the class name.

        Returns:
            List of dicts suitable for serialization or from_simple_data.
        """
        result = []
        for name in self.var_bag.values.keys():
            item = self.var_bag.one_to_simple(name)
            result.append(item)
            color = self.extra_context.get(name, None)
            if color:
                item["bgcolor"] = color
        return result
