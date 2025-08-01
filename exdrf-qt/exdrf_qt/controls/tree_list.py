import logging
from typing import TYPE_CHECKING, Generic, TypeVar, cast

from PyQt5.QtCore import QModelIndex, Qt, pyqtSignal
from PyQt5.QtWidgets import QTreeView

if TYPE_CHECKING:
    from exdrf_qt.models import QtModel

logger = logging.getLogger(__name__)

DBM = TypeVar("DBM")


class TreeView(QTreeView, Generic[DBM]):
    """A tree view that emits a signal when the Enter key is pressed."""

    itemSelected = pyqtSignal(object)

    @property
    def qt_model(self) -> "QtModel[DBM]":
        return cast("QtModel[DBM]", self.model())

    @qt_model.setter
    def qt_model(self, value: "QtModel[DBM]") -> None:
        self.setModel(value)

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
            logger.log(10, "TreeView.currentChanged: no current index")
            self.itemSelected.emit(None)
            return

        item = self.qt_model.data_record(current.row())
        self.itemSelected.emit(item)

        logger.log(
            10,
            "TreeView.currentChanged: %s",
            item.db_id if item else None,
        )
