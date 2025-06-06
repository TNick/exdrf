from typing import TYPE_CHECKING, Any, Optional

from PyQt5.QtWidgets import QAction, QMenu

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401


class AcBase(QAction, QtUseContext):
    """Base class for all actions."""

    route: str

    def __init__(
        self,
        label: str,
        ctx: "QtContext",
        route: str,
        menu_or_parent: Optional[QMenu] = None,
    ):
        super().__init__(label, parent=menu_or_parent)
        self.route = route
        self.ctx = ctx
        self.triggered.connect(self.do_open)
        if isinstance(menu_or_parent, QMenu):
            menu_or_parent.addAction(self)

    def do_open(self):
        """Open the action."""
        raise NotImplementedError("Subclass must implement do_open")


class OpenListAc(AcBase):
    """Action to open a list of a model."""

    route: str

    def do_open(self):
        """Open the list of the model."""
        result = self.ctx.router.route(self.route)
        if isinstance(result, Exception):
            self.ctx.show_error(
                title=self.t("router.open-list.title", "Error opening list"),
                message=self.t(
                    "router.open-list.message",
                    "An error occurred while opening the list at {route}: {e}",
                    route=self.route,
                    e=result,
                ),
            )


class OpenCreateAc(AcBase):
    """Action to open an editor that allows creating a new record."""

    def do_open(self):
        """Create a new record."""
        result = self.ctx.router.route(self.route)
        if isinstance(result, Exception):
            self.ctx.show_error(
                title=self.t(
                    "router.open-create-editor.title",
                    "Error opening the editor",
                ),
                message=self.t(
                    "router.open-create-editor.message",
                    "Error while opening the editor at {route}: {e}",
                    route=self.route,
                    e=result,
                ),
            )


class AcBaseWithId(AcBase):
    """Base class for all actions that have an id."""

    id: Any

    def __init__(
        self,
        label: str,
        menu: QMenu,
        ctx: "QtContext",
        route: str,
        id: Any,
    ):
        """Initialize the action."""
        super().__init__(label, menu, ctx, route)
        self.id = id

    @property
    def str_id(self) -> str:
        """Get the string representation of the id."""
        if isinstance(self.id, int):
            return str(self.id)
        elif isinstance(self.id, str):
            return self.id
        else:
            return ",".join(str(a) for a in self.id)


class OpenEditAc(AcBaseWithId):
    """Action to open an editor that allows editing a record."""

    def do_open(self):
        """Edit a record."""

        route = f"{self.route}/{self.str_id}/edit"
        result = self.ctx.router.route(route)
        if isinstance(result, Exception):
            self.ctx.show_error(
                title=self.t(
                    "router.open-edit-editor.title",
                    "Error opening the editor",
                ),
                message=self.t(
                    "router.open-edit-editor.message",
                    "Error while opening the editor at {route}: {e}",
                    route=self.route,
                    e=result,
                ),
            )


class OpenViewAc(AcBaseWithId):
    """Action to open a viewer that presents a record."""

    def do_open(self):
        """View a record."""

        route = f"{self.route}/{self.str_id}"
        result = self.ctx.router.route(route)
        if isinstance(result, Exception):
            self.ctx.show_error(
                title=self.t(
                    "router.open-edit-editor.title",
                    "Error opening the editor",
                ),
                message=self.t(
                    "router.open-edit-editor.message",
                    "Error while opening the editor at {route}: {e}",
                    route=self.route,
                    e=result,
                ),
            )


class OpenDeleteAc(AcBaseWithId):
    """Action to open a dialog that allows deleting a record."""

    def do_open(self):
        """Delete a record."""

        route = f"{self.route}/{self.str_id}/delete"
        result = self.ctx.router.route(route)
        if isinstance(result, Exception):
            self.ctx.show_error(
                title=self.t(
                    "router.open-delete-dialog.title",
                    "Error opening the delete dialog",
                ),
                message=self.t(
                    "router.open-delete-dialog.message",
                    "Error while opening the delete dialog at {route}: {e}",
                    route=self.route,
                    e=result,
                ),
            )
