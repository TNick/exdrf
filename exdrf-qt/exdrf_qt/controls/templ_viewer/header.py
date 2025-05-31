from typing import TYPE_CHECKING

from exdrf_qt.controls.tree_header import HeaderViewWithMenu

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QMenu, QTreeView

    from exdrf_qt.controls.templ_viewer.templ_viewer import TemplViewer


class VarHeader(HeaderViewWithMenu):
    """The header for a variable table."""

    viewer: "TemplViewer"

    def __init__(self, viewer: "TemplViewer", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.viewer = viewer

    @property
    def qt_model(self):
        return self.viewer.model

    @property
    def treeview(self) -> "QTreeView":
        return self.viewer.c_vars

    def create_show_columns_action(self, menu: "QMenu", section: int):
        return None

    def _load_current_filter(self, section: int):
        if self.search_line:
            if section == 0:
                current_filter = self.viewer.model.name_filter
            else:
                current_filter = self.viewer.model.value_filter
            self.search_line.setText(current_filter)

    def prepare_search_line(self, section: int):
        self._load_current_filter(section)

    def _apply_filter(self, section: int, text: str, exact: bool):
        self.viewer.model.apply_filter(section, text, exact)
