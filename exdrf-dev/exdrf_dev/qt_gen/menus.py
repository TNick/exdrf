# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> menus.py.j2
# Don't change it manually.
import logging
from typing import TYPE_CHECKING, Type

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.seldb.sel_db import SelectDatabaseDlg
from exdrf_qt.controls.table_list import ListDb
from PyQt5.QtWidgets import QAction, QMenu

from exdrf_dev.qt_gen.db.children.api import QtChildList
from exdrf_dev.qt_gen.db.composite_key_models.api import QtCompositeKeyModelList
from exdrf_dev.qt_gen.db.parent_tag_associations.api import (
    QtParentTagAssociationList,
)
from exdrf_dev.qt_gen.db.parents.api import QtParentList
from exdrf_dev.qt_gen.db.profiles.api import QtProfileList
from exdrf_dev.qt_gen.db.related_items.api import QtRelatedItemList
from exdrf_dev.qt_gen.db.tags.api import QtTagList

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------


if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401

logger = logging.getLogger(__name__)
# exdrf-keep-start other_globals ----------------------------------------------

# exdrf-keep-end other_globals ------------------------------------------------


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
            w = self.list_class(ctx=self.ctx)
            if len(w.windowTitle()) == 0:
                w.setWindowTitle(self.text())
            self.ctx.create_window(w, self.text())
        except Exception as e:
            logger.error("Error opening list", exc_info=True)
            self.ctx.show_error(
                title=self.t("cmn.open-list.title", "Error opening list"),
                message=self.t(
                    "cmn.open-list.message",
                    "An error occurred while opening the list: {e}",
                    e=e,
                ),
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

    show_conn_settings_ac: QAction

    # exdrf-keep-start other_menus_attributes ---------------------------------

    # exdrf-keep-end other_menus_attributes -----------------------------------

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

        self.show_conn_settings_ac = QAction("Connection settings", parent)
        self.show_conn_settings_ac.triggered.connect(
            lambda: SelectDatabaseDlg.change_connection_str(ctx)  # type: ignore
        )
        parent.addAction(self.show_conn_settings_ac)
        # exdrf-keep-start extra_menus_init -----------------------------------

        # exdrf-keep-end extra_menus_init -------------------------------------

    # exdrf-keep-start extra_menus_content ------------------------------------

    # exdrf-keep-end extra_menus_content --------------------------------------


# exdrf-keep-start more_content ------------------------------------------------

# exdrf-keep-end more_content --------------------------------------------------
