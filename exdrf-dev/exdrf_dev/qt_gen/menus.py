# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> menus.py.j2
# Don't change it manually.
import logging
from typing import TYPE_CHECKING

from exdrf_qt.controls.crud_actions import OpenListAc
from exdrf_qt.controls.seldb.sel_db import SelectDatabaseDlg
from PyQt5.QtWidgets import QAction, QMenu

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401

logger = logging.getLogger(__name__)
# exdrf-keep-start other_globals ----------------------------------------------

# exdrf-keep-end other_globals ------------------------------------------------


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

        self.db_menu = QMenu(self.ctx.t("menus.db.t", "Db"), parent)
        parent.addMenu(self.db_menu)

        self.open_child_list_ac = OpenListAc(
            self.ctx.t("menus.db.child.list", "Child list"),
            ctx=ctx,
            route="exdrf://navigation/resource/Child",
            menu_or_parent=self.db_menu,
        )

        self.open_composite_key_model_list_ac = OpenListAc(
            self.ctx.t(
                "menus.db.composite_key_model.list", "Composite key model list"
            ),
            ctx=ctx,
            route="exdrf://navigation/resource/CompositeKeyModel",
            menu_or_parent=self.db_menu,
        )

        self.open_parent_list_ac = OpenListAc(
            self.ctx.t("menus.db.parent.list", "Parent list"),
            ctx=ctx,
            route="exdrf://navigation/resource/Parent",
            menu_or_parent=self.db_menu,
        )

        self.open_parent_tag_association_list_ac = OpenListAc(
            self.ctx.t(
                "menus.db.parent_tag_association.list",
                "Parent tag association list",
            ),
            ctx=ctx,
            route="exdrf://navigation/resource/ParentTagAssociation",
            menu_or_parent=self.db_menu,
        )
        self.db_menu.addSeparator()

        self.open_profile_list_ac = OpenListAc(
            self.ctx.t("menus.db.profile.list", "Profile list"),
            ctx=ctx,
            route="exdrf://navigation/resource/Profile",
            menu_or_parent=self.db_menu,
        )

        self.open_related_item_list_ac = OpenListAc(
            self.ctx.t("menus.db.related_item.list", "Related item list"),
            ctx=ctx,
            route="exdrf://navigation/resource/RelatedItem",
            menu_or_parent=self.db_menu,
        )

        self.open_tag_list_ac = OpenListAc(
            self.ctx.t("menus.db.tag.list", "Tag list"),
            ctx=ctx,
            route="exdrf://navigation/resource/Tag",
            menu_or_parent=self.db_menu,
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
