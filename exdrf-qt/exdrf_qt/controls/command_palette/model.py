import logging
from typing import TYPE_CHECKING, Any, List, Optional, cast

from PyQt5.QtCore import QAbstractListModel, QModelIndex, Qt, QVariant

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.command_palette.constants import (
    ICON_ROLE,
    SEARCH_ROLE,
    SUBTITLE_ROLE,
    TITLE_ROLE,
    SearchLocation,
)

if TYPE_CHECKING:
    from PyQt5.QtCore import QObject  # noqa: F401
    from PyQt5.QtGui import QIcon  # noqa: F401

    from exdrf_qt.context import QtContext  # noqa: F401
    from exdrf_qt.menus import ActionDef  # noqa: F401

logger = logging.getLogger(__name__)


class CompleterItemModel(QAbstractListModel, QtUseContext):
    """Custom model for completer items based on action definitions."""

    _action_defs: "List[ActionDef]"
    _default_icon: "QIcon"
    _search_location: SearchLocation
    stg_key: str

    def __init__(
        self,
        ctx: "QtContext",
        default_icon: "QIcon",
        stg_key: str,
        parent: Optional["QObject"] = None,
    ):
        """Initialize the model."""
        super().__init__(parent)
        self.ctx = ctx
        self.stg_key = stg_key
        self._action_defs = []
        self._default_icon = default_icon

        self._search_location = ctx.stg.get_setting(
            f"{stg_key}.search-location", SearchLocation.ALL
        )
        if not self.searches_in_title():
            self._search_location = cast(
                "SearchLocation", self._search_location | SearchLocation.TITLE
            )

    def set_action_defs(self, action_defs: "List[ActionDef]") -> None:
        """Set the action definitions for the command palette."""
        self.beginResetModel()
        self._action_defs = action_defs
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of rows."""
        return len(self._action_defs)

    def data(
        self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        """Return data for the given role."""
        if not index.isValid():
            return QVariant()

        row = index.row()
        if row < 0 or row >= len(self._action_defs):
            logger.error("Invalid index: %s", index)
            return QVariant()

        action_def = self._action_defs[row]

        if role == TITLE_ROLE:
            return action_def.label or ""
        elif role == SUBTITLE_ROLE:
            return action_def.description or ""
        elif role == ICON_ROLE:
            return action_def.icon if action_def.icon else self._default_icon
        elif role == SEARCH_ROLE:
            result = []
            if self._search_location & SearchLocation.TITLE:
                result.append(action_def.label or "")
            if self._search_location & SearchLocation.DESCRIPTION:
                result.append(action_def.description or "")
            if self._search_location & SearchLocation.TAGS:
                result.append("\n".join(action_def.tags))
            return "\n".join(result)
        return QVariant()

    def get_title(self, row: int) -> str:
        """Get the title for the given row."""
        return self._action_defs[row].label or ""

    def get_subtitle(self, row: int) -> str:
        """Get the subtitle for the given row."""
        return self._action_defs[row].description or ""

    def get_action_icon(self, row: int) -> "QIcon":
        """Get the icon for the given row."""
        ac = self._action_defs[row]
        if ac.icon is not None:
            return ac.icon
        return self._default_icon

    def get_action_def(self, row: int) -> "ActionDef":
        """Get the action definition for the given row."""
        return self._action_defs[row]

    def set_search_location(self, search_location: SearchLocation) -> None:
        """Set the search location for the command palette."""
        if search_location == self._search_location:
            return
        self.beginResetModel()
        self._search_location = search_location
        self.endResetModel()
        logger.debug("Search location changed to %s", search_location)
        self.ctx.stg.set_setting(
            f"{self.stg_key}.search-location", int(search_location)
        )

    def searches_in_title(self) -> bool:
        """Check if the model searches in the title."""
        return self._search_location & SearchLocation.TITLE != 0

    def searches_in_description(self) -> bool:
        """Check if the model searches in the description."""
        return self._search_location & SearchLocation.DESCRIPTION != 0

    def searches_in_tags(self) -> bool:
        """Check if the model searches in the tags."""
        return self._search_location & SearchLocation.TAGS != 0
