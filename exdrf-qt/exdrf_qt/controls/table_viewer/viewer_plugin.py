"""Plugin interface for TableViewer."""

from typing import TYPE_CHECKING, List

from PyQt5.QtWidgets import QAction

from exdrf_qt.controls.table_viewer.table_view_ctx import TableViewCtx

if TYPE_CHECKING:
    from exdrf_qt.controls.table_viewer.table_viewer import TableViewer


class ViewerPlugin:
    """Plugin interface for TableViewer.

    Subclasses override methods to contribute actions and be notified when a
    view is created.
    """

    def provide_actions(
        self, viewer: "TableViewer", ctx: TableViewCtx
    ) -> List[QAction]:
        """Return actions for a given view context.

        Args:
            viewer: Hosting viewer.
            ctx: View context for which to provide actions.

        Returns:
            List of actions to add to the context menu.
        """
        return []

    def on_view_created(self, viewer: "TableViewer", ctx: TableViewCtx) -> None:
        """Hook called when a new view is created.

        Args:
            viewer: Hosting viewer.
            ctx: View context that was created.
        """
        return None
