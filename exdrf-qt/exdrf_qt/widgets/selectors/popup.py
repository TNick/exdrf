from typing import TYPE_CHECKING, Optional, cast

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QWidget

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.widgets.selectors.popup_ui import Ui_SelPopup

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401


class SelPopup(QFrame, QtUseContext, Ui_SelPopup):
    """Selector popup widget."""

    mod_width: int
    mod_height: int

    def __init__(
        self, ctx: "QtContext", model, parent: Optional[QWidget] = None
    ):
        super().__init__(
            parent,
            cast(
                Qt.WindowFlags,
                # Popup: Indicates that the widget is a pop-up top-level
                #   window, i.e. that it is modal, but has a window system frame
                #   appropriate for pop-up menus.
                # FramelessWindowHint: Produces a borderless window.
                Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint,
            ),
        )
        self.ctx = ctx
        self.mod_width = 0
        self.mod_height = 0

        self.setup_ui(self)
        self.tree_view.setModel(model)
        self.tree_view.doubleClicked.connect(self.on_item_double_clicked)

        self.clear_button.setIcon(self.get_icon("broom"))
        self.clear_button.clicked.connect(self.on_clear_selection)

        self.pin_button.setIcon(self.get_icon("star"))
        self.pin_button.clicked.connect(self.on_toggle_pinned)

    def resizeEvent(self, event):  # type: ignore[override]
        super().resizeEvent(event)
        self.mod_width = self.width()
        self.mod_height = self.height()

    def on_item_double_clicked(self, index):
        """Handle item double-click event."""

    def on_clear_selection(self):
        """Handle clear selection button click."""

    def on_toggle_pinned(self):
        """Handle toggle pinned button click."""
