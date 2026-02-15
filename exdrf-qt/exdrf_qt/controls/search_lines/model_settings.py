import logging
from typing import TYPE_CHECKING, Generic, List, Optional, TypeVar

from exdrf.filter import SearchType
from PyQt5.QtCore import QPoint

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QAction, QActionGroup, QWidget

    from exdrf_qt.models import QtModel
    from exdrf_qt.utils.stay_open_menu import StayOpenMenu


DBM = TypeVar("DBM")
logger = logging.getLogger(__name__)
VERBOSE = 10


class ModelSearchSettings(Generic[DBM]):
    """A class that handles showing the settings menu for a model."""

    model: "QtModel[DBM]"
    parent: "QWidget"
    menu: "StayOpenMenu"
    ac_group_del: Optional["QActionGroup"]
    ac_group_search: Optional["QActionGroup"]
    ac_simple: List["QAction"]
    search_mode: "SearchType"

    def __init__(self, model: "QtModel[DBM]", parent: "QWidget") -> None:
        from exdrf_qt.utils.stay_open_menu import StayOpenMenu

        self.model = model
        self.parent = parent
        self.menu = StayOpenMenu(parent)
        self.ac_group_del = None
        self.ac_group_search = None
        self.ac_simple = []
        self.search_mode = SearchType.EXACT
        logger.log(VERBOSE, "%s.show_settings()", parent.__class__.__name__)

    def create_search_mode_actions(
        self, current: "SearchType"
    ) -> Optional["QActionGroup"]:
        """Creates a group of actions for the search mode menu."""
        from exdrf_qt.utils.search_actions import (
            create_search_actions,
        )

        ac_group_search = create_search_actions(
            self.model.ctx, current, parent=self.menu
        )
        if ac_group_search is not None:
            if not self.menu.isEmpty():
                self.menu.addSeparator()
            for action in ac_group_search.actions():
                self.menu.addAction(action)

        self.ac_group_search = ac_group_search
        self.search_mode = current
        return ac_group_search

    def create_del_actions(self) -> Optional["QActionGroup"]:
        """Creates a group of actions for the deleted choice menu.

        This allows the user to show only deleted records, only active records,
        or both.
        """
        if not self.model.has_soft_delete_field:
            return None

        from exdrf_qt.utils.del_actions import (
            create_del_actions,
        )

        ac_group_del = create_del_actions(
            self.model.ctx, self.model, parent=self.menu
        )

        if ac_group_del is not None:
            if not self.menu.isEmpty():
                self.menu.addSeparator()
            for action in ac_group_del.actions():
                self.menu.addAction(action)

        self.ac_group_del = ac_group_del
        return ac_group_del

    def create_simple_filtering_actions(self) -> List["QAction"]:
        from exdrf_qt.utils.flt_acts import (
            create_simple_filtering_actions,
        )

        if not self.menu.isEmpty():
            self.menu.addSeparator()
        spl_src_acts = create_simple_filtering_actions(
            self.model.ctx, self.model, parent=self.menu
        )
        if len(spl_src_acts) > 0:
            for action in spl_src_acts:
                self.menu.addAction(action)
        self.ac_simple = spl_src_acts
        return spl_src_acts

    def run(self) -> None:
        """Runs the model settings."""
        if self.menu.isEmpty():
            return

        from exdrf_qt.utils.del_actions import (
            apply_del_action,
        )
        from exdrf_qt.utils.flt_acts import (
            apply_simple_filtering_action,
        )
        from exdrf_qt.utils.search_actions import apply_search_action

        action_widget = self.parent
        widget_rect = action_widget.rect()
        menu_size = self.menu.sizeHint()

        # Calculate the center of the widget
        widget_center_x = widget_rect.left() + widget_rect.width() / 2
        widget_bottom_y = widget_rect.bottom()
        widget_center_local = QPoint(int(widget_center_x), widget_bottom_y)
        widget_center_global = action_widget.mapToGlobal(widget_center_local)

        # Align the menu such that its center matches the widget's center
        menu_pos = widget_center_global
        menu_pos.setX(int(widget_center_global.x() - menu_size.width() / 2))
        self.menu.exec_(menu_pos)

        # Handle simple filtering.
        if self.ac_simple:
            apply_simple_filtering_action(self.ac_simple, self.model)

        # Handle delete choice.
        apply_del_action(self.ac_group_del, self.model)

        # Handle search mode.
        if self.ac_group_search:
            self.search_mode = (
                apply_search_action(self.ac_group_search) or self.search_mode
            )
