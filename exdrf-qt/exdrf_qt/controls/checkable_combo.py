import logging
from typing import TYPE_CHECKING, Any, List, Optional, cast

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import (
    QComboBox,
    QWidget,
)

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext


logger = logging.getLogger(__name__)


class CheckableComboBox(QComboBox, QtUseContext):
    """A combo box whose items are checkable (multi-select).

    This widget extends QComboBox to support multiple selection through
    checkable items. It displays a summary of selected items in the
    display area and provides methods to manage checked state.
    """

    def __init__(
        self,
        ctx: "QtContext",
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the checkable combo box.

        Args:
            ctx: The Qt context.
            parent: Parent widget for proper cleanup.
        """
        super().__init__(parent)
        self.ctx = ctx
        m = QStandardItemModel(self)
        self.setModel(m)
        self.setEditable(False)

    def addCheckItem(self, text: str, checked: bool = False, data: Any = None):
        """Add a checkable item to the combo box.

        Args:
            text: Display text for the item.
            checked: Whether the item should be checked initially.
            data: User data associated with the item.
        """
        model = self.model()
        if not isinstance(model, QStandardItemModel):
            logger.error("Model is not a QStandardItemModel")
            return
        it = QStandardItem(text)
        it.setFlags(
            cast(
                Qt.ItemFlags,
                Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable,
            )
        )
        it.setData(
            Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked,
            Qt.ItemDataRole.CheckStateRole,
        )
        if data is not None:
            it.setData(
                data,
                Qt.ItemDataRole.UserRole,
            )
        model.appendRow(it)
        self._update_text()

    def checkedData(self) -> List[Any]:
        """Get the user data for all checked items.

        Returns:
            List of user data values for checked items.
        """
        model = self.model()
        if not isinstance(model, QStandardItemModel):
            logger.error("Model is not a QStandardItemModel")
            return []

        result: List[Any] = []
        for i in range(model.rowCount()):
            it = model.item(i)
            if it is None:
                continue
            if it.checkState() == Qt.CheckState.Checked:
                result.append(it.data(Qt.ItemDataRole.UserRole))
        return result

    def setCheckedByData(self, values: Optional[List[Any]]):
        """Set checked state for items based on their user data.

        Args:
            values: List of user data values to check. If None, all items
                are checked.
        """
        model = self.model()
        if not isinstance(model, QStandardItemModel):
            logger.error("Model is not a QStandardItemModel")
            return

        for i in range(model.rowCount()):
            it = model.item(i)
            if it is None:
                continue
            data = it.data(Qt.ItemDataRole.UserRole)
            st = (
                Qt.CheckState.Checked
                if (values is None or (values and data in values))
                else Qt.CheckState.Unchecked
            )
            it.setCheckState(st)
        self._update_text()

    def _update_text(self):
        """Update the display text to show selection summary."""
        # Show a friendly summary in the display area
        values = self.checkedData()
        if not values:
            self.setCurrentText(self.t("checkable_combo.none", "(none)"))
            return
        self.setCurrentText(
            self.t(
                "checkable_combo.selected",
                "{len(values)} selected",
                len=len(values),
            )
        )
