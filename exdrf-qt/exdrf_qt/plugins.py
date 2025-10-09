import logging
from typing import TYPE_CHECKING

from pluggy import HookimplMarker, HookspecMarker, PluginManager

if TYPE_CHECKING:
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


# The PluginManager for the exdrf-qt project.
exdrf_qt_pm = PluginManager("exdrf-qt")
exdrf_qt_pm.add_hookspecs(ContextHooks)

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
