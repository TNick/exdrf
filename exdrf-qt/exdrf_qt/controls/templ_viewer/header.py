"""Header widget for the template viewer variables table.

This module provides a ListDbHeader subclass used as the header for the
variables table (name/value columns) in TemplViewer. It wires the
search line to the viewer's VarModel filters and delegates apply_filter
to the model.
"""

from typing import TYPE_CHECKING, Any, Optional

from exdrf_qt.controls.tree_header import ListDbHeader

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QTreeView

    from exdrf_qt.controls.templ_viewer.templ_viewer import TemplViewer


class VarHeader(ListDbHeader):
    """Header for the template viewer variables table (name/value columns).

    Subclasses ListDbHeader with save_settings=False and no qt_model;
    the viewer's VarModel is used via viewer.model. The search line is
    synced with the model's name_filter (section 0) or value_filter
    (section 1), and filter application is delegated to the model.

    Attributes:
        viewer: The TemplViewer that owns the variables table and model.
    """

    viewer: "TemplViewer"

    def __init__(
        self,
        viewer: "TemplViewer",
        **kwargs: Any,
    ) -> None:
        """Initialize the header with the template viewer.

        Args:
            viewer: TemplViewer that owns the variables table and
                VarModel (viewer.model).
            **kwargs: Passed to ListDbHeader (e.g. parent).
        """
        super().__init__(
            save_settings=False, qt_model=None, **kwargs  # type: ignore
        )  # type: ignore
        self.viewer = viewer

    @property
    def treeview(self) -> "QTreeView":
        """Return the variables table tree view (viewer.c_vars)."""
        return self.viewer.c_vars

    def create_show_columns_action(self, section: int) -> Optional[Any]:
        """Return no column-visibility action; table has fixed columns.

        Args:
            section: Column section index (unused).

        Returns:
            None (no action for this header).
        """
        return None

    def _load_current_filter(self, section: int) -> None:
        """Populate the search line with the model's current filter.

        If search_line exists, sets its text to name_filter (section 0)
        or value_filter (section 1) from the viewer's model.

        Args:
            section: Column index; 0 for name filter, 1 for value filter.
        """
        if self.search_line:
            if section == 0:
                current_filter = self.viewer.model.name_filter
            else:
                current_filter = self.viewer.model.value_filter
            self.search_line.setText(current_filter)

    def prepare_search_line(self, section: int) -> None:
        """Prepare the search line when the user focuses a column.

        Loads the current filter for that section. Called by the base
        header when the search line is shown for a
        section. Loads the model's filter for that section into the
        search line.

        Args:
            section: Column index; 0 for name, 1 for value.
        """
        self._load_current_filter(section)

    def _apply_filter(self, section: int, text: str, exact: bool) -> None:
        """Apply the filter to the viewer's model for the given section.

        Delegates to viewer.model.apply_filter with the same arguments.
        Called by the base header when the user commits a search.

        Args:
            section: Column index; 0 to filter by name, 1 by value.
            text: Filter text.
            exact: Whether to require exact match.
        """
        self.viewer.model.apply_filter(section, text, exact)
