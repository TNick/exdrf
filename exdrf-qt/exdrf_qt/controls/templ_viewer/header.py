from typing import TYPE_CHECKING

from exdrf_qt.controls.tree_header import ListDbHeader

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QTreeView

    from exdrf_qt.controls.templ_viewer.templ_viewer import TemplViewer


class VarHeader(ListDbHeader):
    """The header for a variable table."""

    viewer: "TemplViewer"

    def __init__(
        self,
        viewer: "TemplViewer",
        **kwargs,
    ):
        super().__init__(save_settings=False, **kwargs)  # type: ignore
        self.viewer = viewer

    @property
    def treeview(self) -> "QTreeView":
        return self.viewer.c_vars

    def create_show_columns_action(self, section: int):
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
