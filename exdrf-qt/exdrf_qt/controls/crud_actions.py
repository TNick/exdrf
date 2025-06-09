from typing import TYPE_CHECKING, Any, Optional

from PyQt5.QtGui import QIcon
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
        icon: Optional[QIcon] = None,
    ):
        super().__init__(label, parent=menu_or_parent)
        self.route = route
        self.ctx = ctx
        self.triggered.connect(self.do_open)
        if isinstance(menu_or_parent, QMenu):
            menu_or_parent.addAction(self)
        if icon is not None:
            self.setIcon(icon)

    def do_open(self):
        """Open the list of the model."""
        result = self.ctx.router.route(self.route)
        if isinstance(result, Exception):
            self.ctx.show_error(
                title=self.t("router.err-open.title", "Error opening route"),
                message=self.t(
                    "router.err-open.message",
                    "An error occurred while opening route {route}: {e}",
                    route=self.route,
                    e=result,
                ),
            )


class OpenListAc(AcBase):
    """Action to open a list of a model."""

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

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.setIcon(self.get_icon("document_empty"))

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
        ctx: "QtContext",
        route: str,
        id: Any,
        menu_or_parent: Optional[QMenu] = None,
    ):
        """Initialize the action."""
        super().__init__(label, ctx, route, menu_or_parent=menu_or_parent)
        self.id = id

    @property
    def str_id(self) -> str:
        """Get the string representation of the id."""
        if callable(self.id):
            true_id = self.id()
        else:
            true_id = self.id

        if true_id is None:
            return ""

        if isinstance(true_id, int):
            return str(true_id)
        elif isinstance(true_id, str):
            return true_id
        else:
            return ",".join(str(a) for a in true_id)


class OpenEditAc(AcBaseWithId):
    """Action to open an editor that allows editing a record.

    You can either provide wither the ID or a function that returns the ID of
    the record to be deleted.
    """

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.setIcon(self.get_icon("edit_button"))

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
    """Action to open a viewer that presents a record.

    You can either provide wither the ID or a function that returns the ID of
    the record to be deleted.
    """

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.setIcon(self.get_icon("eye"))

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
    """Action to open a dialog that allows deleting a record.

    You can either provide wither the ID or a function that returns the ID of
    the record to be deleted.
    """

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.setIcon(self.get_icon("cross"))

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
