from typing import TYPE_CHECKING, Generic, Optional, TypeVar

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QLineEdit

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget  # noqa: F401

    from exdrf_qt.context import QtContext  # noqa: F401
    from exdrf_qt.models import QtModel  # noqa: F401


DBM = TypeVar("DBM")


class SingleSelDb(QLineEdit, QtUseContext, Generic[DBM]):
    """A combo-box that allows the user to select a single item from a database
    table.
    """

    qt_model: "QtModel[DBM]"

    selectedItemsChanged = pyqtSignal(list)  # type: ignore[valid-type]

    def __init__(
        self,
        ctx: "QtContext",
        qt_model: "QtModel[DBM]",
        parent: Optional["QWidget"] = None,
    ):
        super().__init__(parent=parent)
        self.ctx = ctx
        self.qt_model = qt_model
        self.setReadOnly(True)
        self.setPlaceholderText(self.t("cmn.select", "Select an item"))
