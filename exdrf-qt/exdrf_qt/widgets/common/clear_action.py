from typing import Optional

from PyQt5.QtWidgets import QAction, QMenu, QStyle, QWidget


def create_clear_action(
    widget: QWidget, menu: Optional[QMenu] = None
) -> QAction:
    """Create a clear_to_null action for the field editor.

    Args:
        menu: The menu to add the action to.

    Returns:
        The created action.
    """
    style = widget.style()  # type: ignore
    assert style is not None

    if menu:
        clear_action = menu.addAction(
            style.standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton),
            "Set to Null",
        )
    else:
        clear_action = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton),
            "Set to Null",
        )
        clear_action.setToolTip("Set to NULL")
        clear_action.setShortcut("Del")
    assert clear_action is not None
    clear_action.triggered.connect(widget.clear_to_null)

    widget.clear_ac = clear_action
    clear_action.setEnabled(widget._nullable)
    return clear_action
