import logging
from typing import TYPE_CHECKING, Type

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.widgets.lists import ListDb
from PyQt5.QtWidgets import QAction, QMenu

from exdrf_dev.qt.children.api import QtChildList
from exdrf_dev.qt.composite_key_models.api import QtCompositeKeyModelList
from exdrf_dev.qt.parent_tag_associations.api import QtParentTagAssociationList
from exdrf_dev.qt.parents.api import QtParentList
from exdrf_dev.qt.profiles.api import QtProfileList
from exdrf_dev.qt.related_items.api import QtRelatedItemList
from exdrf_dev.qt.tags.api import QtTagList

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401

logger = logging.getLogger(__name__)


class OpenListAc(QAction, QtUseContext):
    """Action to open a list of a model."""

    list_class: Type[ListDb]

    def __init__(
        self,
        label: str,
        menu: QMenu,
        ctx: "QtContext",
        list_class: Type[ListDb],
    ):
        """Initialize the action."""
        super().__init__(label, menu)
        self.list_class = list_class
        self.ctx = ctx
        self.triggered.connect(self.open_list)
        menu.addAction(self)

    def open_list(self):
        """Open the list of the model."""
        try:
            if not self.ctx.ensure_db_conn():
                return
            self.ctx.create_window(self.list_class(ctx=self.ctx))
        except Exception as e:
            logger.error("Error opening list", exc_info=True)
            self.ctx.show_error(
                title="Error opening list",
                message=f"An error occurred while opening the list: {e}",
            )
            return


class ExdrfMenus:
    """Contains all the actions and menus for the application."""

    db_menu: QMenu

    open_child_list_ac: OpenListAc
    open_composite_key_model_list_ac: OpenListAc
    open_parent_list_ac: OpenListAc
    open_parent_tag_association_list_ac: OpenListAc
    open_profile_list_ac: OpenListAc
    open_related_item_list_ac: OpenListAc
    open_tag_list_ac: OpenListAc

    def __init__(self, ctx: "QtContext", parent: QMenu):
        """Initialize the menus."""
        self.ctx = ctx

        self.db_menu = QMenu("Db", parent)
        parent.addMenu(self.db_menu)

        self.open_child_list_ac = OpenListAc(
            "Child list",
            self.db_menu,
            ctx,
            QtChildList,
        )
        self.open_composite_key_model_list_ac = OpenListAc(
            "Composite key model list",
            self.db_menu,
            ctx,
            QtCompositeKeyModelList,
        )
        self.open_parent_list_ac = OpenListAc(
            "Parent list",
            self.db_menu,
            ctx,
            QtParentList,
        )
        self.open_parent_tag_association_list_ac = OpenListAc(
            "Parent tag association list",
            self.db_menu,
            ctx,
            QtParentTagAssociationList,
        )
        self.open_profile_list_ac = OpenListAc(
            "Profile list",
            self.db_menu,
            ctx,
            QtProfileList,
        )
        self.open_related_item_list_ac = OpenListAc(
            "Related item list",
            self.db_menu,
            ctx,
            QtRelatedItemList,
        )
        self.open_tag_list_ac = OpenListAc(
            "Tag list",
            self.db_menu,
            ctx,
            QtTagList,
        )
