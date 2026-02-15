import logging
from typing import TYPE_CHECKING, Generic, Optional, TypeVar, cast

from PyQt5.QtCore import (
    QAbstractItemModel,
    QItemSelection,
    QModelIndex,
    Qt,
    pyqtSignal,
)
from PyQt5.QtWidgets import QTreeView

if TYPE_CHECKING:
    from exdrf_qt.models import QtModel

logger = logging.getLogger(__name__)
VERBOSE = 1

DBM = TypeVar("DBM")


class TreeView(QTreeView, Generic[DBM]):
    """A tree view that emits a signal when the Enter key is pressed."""

    itemSelected = pyqtSignal(object)
    itemsSelected = pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        sm = self.selectionModel()
        if sm is not None:
            sm.selectionChanged.connect(self.on_selection_changed)

    @property
    def qt_model(self) -> "QtModel[DBM]":
        return cast("QtModel[DBM]", self.model())

    @qt_model.setter
    def qt_model(self, value: "QtModel[DBM]") -> None:
        self.setModel(value)

    def setModel(self, model: Optional["QAbstractItemModel"]) -> None:
        sm = self.selectionModel()
        if sm is not None:
            sm.selectionChanged.disconnect(self.on_selection_changed)
        super().setModel(model)
        sm = self.selectionModel()
        if sm is not None:
            sm.selectionChanged.connect(self.on_selection_changed)

    def keyPressEvent(self, event):
        assert event is not None
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            index = self.currentIndex()
            if index.isValid():
                self.setCurrentIndex(index)
        else:
            super().keyPressEvent(event)

    def currentChanged(
        self, current: QModelIndex, previous: QModelIndex
    ) -> None:
        if not current or not current.isValid():
            logger.log(VERBOSE, "TreeView.currentChanged: no current index")
            self.itemSelected.emit(None)
            return

        item = self.qt_model.data_record(current.row())
        self.itemSelected.emit(item)

        logger.log(
            1,
            "TreeView.currentChanged: %s",
            item.db_id if item else None,
        )

    def on_selection_changed(
        self, selected: QItemSelection, deselected: QItemSelection
    ) -> None:
        """Handle the selection changed signal.

        Args:
            selected: The selected items.
            deselected: The deselected items.
        """
        logger.log(
            VERBOSE, "TreeView.on_selection_changed: %s", selected, deselected
        )
        sm = self.selectionModel()
        if sm is None:
            self.itemsSelected.emit([])
            return

        # Get all currently selected indices, not just the ones that changed
        indices = sm.selectedIndexes()
        if not indices:
            self.itemsSelected.emit([])
            return

        logger.log(VERBOSE, "Selected indices: %s", [i.row() for i in indices])
        items = [self.qt_model.data_record(index.row()) for index in indices]
        self.itemsSelected.emit(items)
