from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, cast

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCompleter,
    QListView,
    QStyle,
    QStyleOptionViewItem,
    QWidget,
)

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.command_palette.constants import (
    MAX_POPUP_WIDTH,
    SEARCH_ROLE,
)
from exdrf_qt.controls.command_palette.delegate import CompleterItemDelegate
from exdrf_qt.controls.command_palette.model import CompleterItemModel

if TYPE_CHECKING:
    from PyQt5.QtGui import QIcon, QShowEvent  # noqa: F401

    from exdrf_qt.context import QtContext  # noqa: F401
    from exdrf_qt.controls.command_palette.constants import (  # noqa: F401
        SearchLocation,
    )
    from exdrf_qt.menus import ActionDef  # noqa: F401


class CompleterListView(QListView):
    """Custom QListView that updates width when shown."""

    _engine: Optional["ComEngine"]

    def __init__(self, parent: "QWidget", engine: "ComEngine"):
        """Initialize the list view."""
        super().__init__(parent)
        self._engine = engine

    def showEvent(self, a0: "QShowEvent | None") -> None:
        """Update popup width when shown."""
        super().showEvent(a0)
        # Use a timer to ensure the model is fully filtered before
        # calculating width. This is especially important when typing
        # triggers the completer, as the proxy model may still be filtering.
        engine = self._engine
        if engine is not None:
            QTimer.singleShot(0, lambda: engine._update_popup_width(self))


class ComEngine(QCompleter, QtUseContext):
    completer_model: CompleterItemModel
    delegate: Optional[CompleterItemDelegate]
    stg_key: str

    def __init__(
        self,
        ctx: "QtContext",
        default_icon: "QIcon",
        parent: "QWidget",
        stg_key: str,
    ):
        super().__init__(parent)
        self.ctx = ctx
        self.stg_key = stg_key
        self.delegate = None
        self.completer_model = CompleterItemModel(
            ctx=self.ctx,
            default_icon=default_icon,
            stg_key=stg_key,
            parent=self,
        )
        self.setCompletionRole(SEARCH_ROLE)
        self.setCompletionMode(
            QCompleter.CompletionMode.PopupCompletion
            # QCompleter.CompletionMode.UnfilteredPopupCompletion
        )
        self.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setModel(self.completer_model)
        self._setup_popup(parent=parent)

    def _setup_popup(self, parent: "QWidget") -> None:
        """Setup the popup for the completer."""
        lst = CompleterListView(parent=parent, engine=self)

        # Enable variable height items
        lst.setUniformItemSizes(False)

        self.setPopup(lst)

    def setPopup(self, popup: Optional[QAbstractItemView]) -> None:
        """Set the popup for the completer.

        The Qt implementation of this function sets the delegate unconditionally
        so we have no choice but to override it so that we can install
        our own delegate.
        """
        super().setPopup(popup)
        if popup is None:
            return

        lst = cast(QListView, popup)
        if self.delegate is None:
            self.delegate = CompleterItemDelegate(lst)
        else:
            self.delegate.setParent(lst)
        lst.setItemDelegate(self.delegate)

        self._update_popup_width(lst)

    def _update_popup_width(self, popup: "QListView") -> None:
        """Update popup width to fit longest item, max MAX_POPUP_WIDTH."""
        if self.delegate is None:
            return

        # Get font metrics from the popup
        font = popup.font()
        option = QStyleOptionViewItem()
        option.font = font
        option.widget = popup

        # Use the popup's model (which may be a filtered proxy model)
        # instead of the completer's model to get the actual displayed items
        model = popup.model()
        if model is None:
            model = self.model()

        # Find the maximum width needed for content
        max_content_width = 0
        if model:
            for row in range(model.rowCount()):
                index = model.index(row, 0)
                size_hint = self.delegate.sizeHint(option, index)
                max_content_width = max(max_content_width, size_hint.width())

        # Check if vertical scrollbar will be visible
        # Estimate based on whether items exceed maxVisibleItems
        max_visible = self.maxVisibleItems()
        will_have_scrollbar = (
            model and model.rowCount() > max_visible if model else False
        )

        # Get scrollbar width if it will be visible
        scrollbar_width = 0
        if will_have_scrollbar:
            style = popup.style()
            if style:
                # Get scrollbar width from style
                scrollbar_width = style.pixelMetric(
                    QStyle.PixelMetric.PM_ScrollBarExtent
                )

        # Get frame width (border/padding of the list view)
        frame_width = popup.frameWidth() * 2  # Left + right frame

        # Total width needed: content + scrollbar (if visible) + frame
        total_width = max_content_width + scrollbar_width + frame_width

        # Set width to minimum of total_width and MAX_POPUP_WIDTH
        popup_width = min(total_width, MAX_POPUP_WIDTH)
        popup.setMinimumWidth(popup_width)
        popup.setMaximumWidth(popup_width)

        # Disable horizontal scrollbar
        popup.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

    def complete(self, rect=None) -> None:
        """Override to update popup width before showing."""
        # Width will be updated in showEvent of CompleterListView
        if rect is None:
            super().complete()
        else:
            super().complete(rect)

    def set_action_defs(self, action_defs: "List[ActionDef]") -> None:
        """Set the action definitions for the command palette."""
        self.completer_model.set_action_defs(action_defs)

    def get_action_def(self, row: int) -> "ActionDef":
        """Get the action definition for the given row."""
        return self.completer_model.get_action_def(row)

    def set_search_location(self, search_location: "SearchLocation") -> None:
        """Set the search location for the command palette."""
        self.completer_model.set_search_location(search_location)
