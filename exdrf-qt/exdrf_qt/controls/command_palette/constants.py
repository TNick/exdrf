from enum import IntEnum

from PyQt5.QtCore import Qt

# Maximum width for completer popup in pixels.
MAX_POPUP_WIDTH = 500

# Maximum width for line edit in pixels.
MAX_LINE_EDIT_WIDTH = 200


SEARCH_ROLE = Qt.ItemDataRole.EditRole
TITLE_ROLE = Qt.ItemDataRole.DisplayRole
SUBTITLE_ROLE = Qt.ItemDataRole.UserRole + 2
ICON_ROLE = Qt.ItemDataRole.DecorationRole


ICON_SIZE = 24
PADDING = 8

TITLE_FONT_FACTOR = 1.1
SUBTITLE_FONT_FACTOR = 0.95

SPACING_BETWEEN_TITLE_AND_SUBTITLE = 2


class SearchLocation(IntEnum):
    """Locations to search in for the command palette."""

    NONE = 0
    """No locations to search in."""
    TITLE = 1
    """Search in the title."""
    DESCRIPTION = 2
    """Search in the description."""
    TAGS = 4
    """Search in the tags."""
    ALL = TITLE | DESCRIPTION | TAGS
    """Search in all locations."""
