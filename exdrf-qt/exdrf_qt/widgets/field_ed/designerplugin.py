"""Work in progress.

The designer plugin for ExDrf widgets.

This is a work in progress. The goal is to create a plugin that can be used in
Qt Designer to create ExDrf widgets.
"""

import os

from PyQt5.QtDesigner import (
    QDesignerFormEditorInterface,
    QPyDesignerCustomWidgetCollectionPlugin,
    QPyDesignerCustomWidgetPlugin,
)
from PyQt5.QtGui import QIcon

debug_path = os.path.join(
    os.path.dirname(__file__),
    os.path.pardir,
    os.path.pardir,
    os.path.pardir,
    "playground",
    "designer-plugin.log",
)


def create_plugin_class(widget_class, include_file, group_name):
    class AutoPlugin(QPyDesignerCustomWidgetPlugin):
        f"""Auto-generated plugin class for {widget_class.__name__}."""

        def __init__(self, parent=None):
            super().__init__(parent)
            self.initialized = False

        def initialize(self, core):
            if self.initialized:
                return
            self.initialized = True

        def isInitialized(self):
            return self.initialized

        def createWidget(self, parent):
            return widget_class(parent)

        def name(self):
            return widget_class.__name__

        def group(self):
            return group_name

        def icon(self):
            # Access the built-in icons from QDesignerFormEditorInterface
            core = QDesignerFormEditorInterface()
            # use getattr to avoid unknown‐attribute warnings
            icon_cache_fn = getattr(core, "iconCache", None)
            if icon_cache_fn:
                cache = icon_cache_fn()
                # icon = cache.icon(":/trolltech/formeditor/images/plus.png")
                # if not icon.isNull():
                #     return icon
                with open(debug_path, "w", encoding="utf-8") as f:
                    for icon_name in cache.iconNames():
                        f.write(icon_name)
                        f.write("\n")
            else:
                with open(debug_path, "w", encoding="utf-8") as f:
                    f.write("iconCache is None")
                    f.write("\n")

            # fallback default
            return QIcon()

        def toolTip(self):
            return f"A custom widget: {widget_class.__name__}"

        def whatsThis(self):
            return f"This is {widget_class.__name__}"

        def isContainer(self):
            return False

        def includeFile(self):
            return include_file

    return AutoPlugin


class ExDrfCollectionPlugin(QPyDesignerCustomWidgetCollectionPlugin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.plugins = []
        for file_name in os.listdir(os.path.dirname(__file__)):
            if file_name.endswith(".py") and file_name not in (
                "__init__.py",
                "fed_base.py",
                "designer_plugin.py",
            ):
                module_name = file_name[:-3]
                module = __import__(module_name, fromlist=[module_name])
                widget_class = getattr(module, module_name)
                group_name = "ExDrf Widgets"

                # Create a plugin class for the widget
                self.plugins.append(
                    create_plugin_class(widget_class, file_name, group_name)
                )


with open(debug_path, "w", encoding="utf-8") as f:
    f.write("imported")
    f.write("\n")
