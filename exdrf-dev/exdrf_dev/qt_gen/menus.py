# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> menus.py.j2
# Don't change it manually.
import logging
from functools import partial
from typing import TYPE_CHECKING, Dict, List

from exdrf_qt.controls.crud_actions import (
    follow_create_route,
    follow_list_route,
)
from exdrf_qt.controls.seldb.sel_db import SelectDatabaseDlg
from exdrf_qt.menus import ActionDef, DefBase, MenuDef
from exdrf_qt.plugins import exdrf_qt_pm, hook_impl
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401

logger = logging.getLogger(__name__)
# exdrf-keep-start other_globals ----------------------------------------------

# exdrf-keep-end other_globals ------------------------------------------------


class ExdrfMenus:
    """Contains all the actions and menus for the application.

    This class implements the create_extra_main_menu_defs hook to provide
    menu definitions for all resources. The hook is automatically registered
    when the class is instantiated.
    """

    ctx: "QtContext"
    _created: Dict[str, "QAction"]

    # exdrf-keep-start other_menus_attributes ---------------------------------

    # exdrf-keep-end other_menus_attributes -----------------------------------

    def __init__(self, ctx: "QtContext", parent: QMenu = None):
        """Initialize the menus.

        Args:
            ctx: The Qt context for accessing translations, icons, and database
                connections.
            parent: Optional parent menu (deprecated, not used with hook system).
        """
        self.ctx = ctx
        self._created = {}

        # Register this instance as a plugin to provide menu definitions.
        exdrf_qt_pm.register(self, name="exdrf_menus")

        # exdrf-keep-start extra_menus_init -----------------------------------

        # exdrf-keep-end extra_menus_init -------------------------------------

    @property
    def show_conn_settings_ac(self) -> "QAction":
        """Get the connection settings action from the created dictionary."""
        return self._created.get("show_conn_settings")  # type: ignore

    @hook_impl()
    def create_extra_main_menu_defs(  # type: ignore
        self, ctx: "QtContext"  # type: ignore
    ) -> List["DefBase"]:
        """Hook implementation that provides menu definitions for all resources.

        Args:
            ctx: The Qt context for accessing translations, icons, and database
                connections.

        Returns:
            List[DefBase]: A list of menu and action definitions.
        """
        result: List["DefBase"] = []

        # Create menu definitions for each category.

        result.append(
            MenuDef(
                key="db-menu",
                label=ctx.t("menus.db.t", "Db"),
                parent=("concerns-menu",),
                rules=(),
            )
        )

        # Create action definitions for each resource in this category.

        route_child = "exdrf://navigation/resource/Child"
        route_create_child = "exdrf://navigation/resource/Child/create"

        # List action (shown in menu)
        result.append(
            ActionDef(
                key="open_child_list",
                label=ctx.t("menus.db.child.list.t", "Child list"),
                parent=("db-menu",),
                rules=(),
                callback=partial(follow_list_route, ctx=ctx, route=route_child),
            )
        )

        # Create action (not shown in menu, available via command palette)
        result.append(
            ActionDef(
                key="create_child",
                label=ctx.t("menus.db.child.create.t", "Create Child"),
                parent=(),
                rules=(),
                callback=partial(
                    follow_create_route, ctx=ctx, route=route_create_child
                ),
                description=ctx.t(
                    "menus.db.child.create.d", "Create a new Child"
                ),
                no_menu=True,
            )
        )
        route_composite_key_model = (
            "exdrf://navigation/resource/CompositeKeyModel"
        )
        route_create_composite_key_model = (
            "exdrf://navigation/resource/CompositeKeyModel/create"
        )

        # List action (shown in menu)
        result.append(
            ActionDef(
                key="open_composite_key_model_list",
                label=ctx.t(
                    "menus.db.composite_key_model.list.t",
                    "Composite key model list",
                ),
                parent=("db-menu",),
                rules=(),
                callback=partial(
                    follow_list_route, ctx=ctx, route=route_composite_key_model
                ),
            )
        )

        # Create action (not shown in menu, available via command palette)
        result.append(
            ActionDef(
                key="create_composite_key_model",
                label=ctx.t(
                    "menus.db.composite_key_model.create.t",
                    "Create Composite key model",
                ),
                parent=(),
                rules=(),
                callback=partial(
                    follow_create_route,
                    ctx=ctx,
                    route=route_create_composite_key_model,
                ),
                description=ctx.t(
                    "menus.db.composite_key_model.create.d",
                    "Create a new Composite key model",
                ),
                no_menu=True,
            )
        )
        route_parent = "exdrf://navigation/resource/Parent"
        route_create_parent = "exdrf://navigation/resource/Parent/create"

        # List action (shown in menu)
        result.append(
            ActionDef(
                key="open_parent_list",
                label=ctx.t("menus.db.parent.list.t", "Parent list"),
                parent=("db-menu",),
                rules=(),
                callback=partial(
                    follow_list_route, ctx=ctx, route=route_parent
                ),
            )
        )

        # Create action (not shown in menu, available via command palette)
        result.append(
            ActionDef(
                key="create_parent",
                label=ctx.t("menus.db.parent.create.t", "Create Parent"),
                parent=(),
                rules=(),
                callback=partial(
                    follow_create_route, ctx=ctx, route=route_create_parent
                ),
                description=ctx.t(
                    "menus.db.parent.create.d", "Create a new Parent"
                ),
                no_menu=True,
            )
        )
        route_profile = "exdrf://navigation/resource/Profile"
        route_create_profile = "exdrf://navigation/resource/Profile/create"

        # List action (shown in menu)
        result.append(
            ActionDef(
                key="open_profile_list",
                label=ctx.t("menus.db.profile.list.t", "Profile list"),
                parent=("db-menu",),
                rules=(),
                callback=partial(
                    follow_list_route, ctx=ctx, route=route_profile
                ),
            )
        )

        # Create action (not shown in menu, available via command palette)
        result.append(
            ActionDef(
                key="create_profile",
                label=ctx.t("menus.db.profile.create.t", "Create Profile"),
                parent=(),
                rules=(),
                callback=partial(
                    follow_create_route, ctx=ctx, route=route_create_profile
                ),
                description=ctx.t(
                    "menus.db.profile.create.d", "Create a new Profile"
                ),
                no_menu=True,
            )
        )
        route_related_item = "exdrf://navigation/resource/RelatedItem"
        route_create_related_item = (
            "exdrf://navigation/resource/RelatedItem/create"
        )

        # List action (shown in menu)
        result.append(
            ActionDef(
                key="open_related_item_list",
                label=ctx.t(
                    "menus.db.related_item.list.t", "Related item list"
                ),
                parent=("db-menu",),
                rules=(),
                callback=partial(
                    follow_list_route, ctx=ctx, route=route_related_item
                ),
            )
        )

        # Create action (not shown in menu, available via command palette)
        result.append(
            ActionDef(
                key="create_related_item",
                label=ctx.t(
                    "menus.db.related_item.create.t", "Create Related item"
                ),
                parent=(),
                rules=(),
                callback=partial(
                    follow_create_route,
                    ctx=ctx,
                    route=route_create_related_item,
                ),
                description=ctx.t(
                    "menus.db.related_item.create.d",
                    "Create a new Related item",
                ),
                no_menu=True,
            )
        )
        route_tag = "exdrf://navigation/resource/Tag"
        route_create_tag = "exdrf://navigation/resource/Tag/create"

        # List action (shown in menu)
        result.append(
            ActionDef(
                key="open_tag_list",
                label=ctx.t("menus.db.tag.list.t", "Tag list"),
                parent=("db-menu",),
                rules=(),
                callback=partial(follow_list_route, ctx=ctx, route=route_tag),
            )
        )

        # Create action (not shown in menu, available via command palette)
        result.append(
            ActionDef(
                key="create_tag",
                label=ctx.t("menus.db.tag.create.t", "Create Tag"),
                parent=(),
                rules=(),
                callback=partial(
                    follow_create_route, ctx=ctx, route=route_create_tag
                ),
                description=ctx.t("menus.db.tag.create.d", "Create a new Tag"),
                no_menu=True,
            )
        )

        # Add connection settings action at the end of concerns menu.
        result.append(
            ActionDef(
                key="show_conn_settings",
                label=ctx.t(
                    "menus.connection_settings.t", "Connection settings"
                ),
                description=ctx.t(
                    "menus.connection_settings.d",
                    "Define connection parameters and save them for later "
                    "use.\n"
                    "The database can also be initialized from this dialog.",
                ),
                parent=("concerns-menu",),
                rules=(),
                callback=partial(
                    SelectDatabaseDlg.change_connection_str, ctx
                ),  # type: ignore
            )
        )

        return result

    def adjust_icons(self, created: Dict[str, "QAction"]):
        """Adjust icons for actions after they have been created.

        This method can be overridden or extended to customize icons for
        specific actions. The created dictionary maps action keys to QAction
        instances.

        Args:
            created: Dictionary mapping action keys to created QAction instances.
        """
        # Store reference to created dictionary for property access.
        self._created = created

        # exdrf-keep-start adjust_icons_content ---------------------------------
        # Override this section to customize icons.
        # Example:
        # if "open_immobile_list" in created:
        #     created["open_immobile_list"].setIcon(self.ctx.get_icon("c_land"))
        # exdrf-keep-end adjust_icons_content -----------------------------------

    # exdrf-keep-start extra_menus_content ------------------------------------

    # exdrf-keep-end extra_menus_content --------------------------------------


# exdrf-keep-start more_content ------------------------------------------------

# exdrf-keep-end more_content --------------------------------------------------
