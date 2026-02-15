import logging
from typing import TYPE_CHECKING

from pluggy import HookimplMarker, HookspecMarker, PluginManager

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QMenu, QTableView, QWidget

    from exdrf_qt.context import QtContext


hook_spec = HookspecMarker("exdrf-qt")
hook_impl = HookimplMarker("exdrf-qt")

logger = logging.getLogger(__name__)


class ContextHooks:
    """Hooks related to the QtContext."""

    context_created_impl = HookimplMarker("exdrf-qt")(
        specname="context_created"
    )

    @hook_spec
    def context_created(self, context: "QtContext") -> None:
        """Called when a context is created."""
        raise NotImplementedError


class TransferHooks:
    """Hooks for the transfer widget (source/destination table lists).

    Plugins can add menu items to the context menu shown when right-clicking
    the source or destination table list.
    """

    @hook_spec
    def transfer_context_menu(
        self,
        transfer_widget: "QWidget",
        menu: "QMenu",
        view: "QTableView",
        is_source_side: bool,
    ) -> None:
        """Called when the context menu is about to be shown for a table list.

        Implementations may add actions (or submenus) to `menu`. The menu is
        shown for either the source pane or the destination pane.

        Args:
            transfer_widget: The TransferWidget instance (for ctx, connections).
            menu: The context menu to extend.
            view: The table view that was right-clicked.
            is_source_side: True if the menu is for the source list, False for
                the destination list.
        """
        raise NotImplementedError


# The PluginManager for the exdrf-qt project.
exdrf_qt_pm = PluginManager("exdrf-qt")
exdrf_qt_pm.add_hookspecs(ContextHooks)
exdrf_qt_pm.add_hookspecs(TransferHooks)

# To have your plugin automatically loaded, add an entry point to your
# setup.py file.
#
# [options.entry_points]
# exdrf-qt =
#     french = hello_plugin.hello_plugin:FrenchPlugin
#
# The `french` is the name of the plugin. The `hello_plugin.hello_plugin` is
# the module and class name of the plugin.
#
exdrf_qt_pm.load_setuptools_entrypoints("exdrf_qt")
