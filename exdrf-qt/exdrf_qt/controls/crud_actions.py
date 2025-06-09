from typing import TYPE_CHECKING, Any, Callable, Optional, Union

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QMenu
from sqlalchemy import Select

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from sqlalchemy.orm import Session  # noqa: F401

    from exdrf_qt.context import QtContext  # noqa: F401


def follow_del_route(ctx: "QtContext", route: Union[None, str], **kwargs):
    if route is None:
        return None
    e = ctx.router.route(route, **kwargs)
    if isinstance(e, Exception):
        ctx.show_error(
            title=ctx.t("router.open-delete.title", "Error opening delete"),
            message=ctx.t(
                "router.open-delete.message",
                "An error occurred while opening the delete at {route}: {e}",
                route=route,
                e=e,
            ),
        )
    return e


def follow_view_route(ctx: "QtContext", route: Union[None, str]):
    if route is None:
        return None
    e = ctx.router.route(route)
    if isinstance(e, Exception):
        ctx.show_error(
            title=ctx.t("router.open-view.title", "Error opening view"),
            message=ctx.t(
                "router.open-view.message",
                "An error occurred while opening the view at {route}: {e}",
                route=route,
                e=e,
            ),
        )
    return e


def follow_edit_route(ctx: "QtContext", route: Union[None, str]):
    if route is None:
        return None
    e = ctx.router.route(route)
    if isinstance(e, Exception):
        ctx.show_error(
            title=ctx.t("router.open-edit.title", "Error opening edit"),
            message=ctx.t(
                "router.open-edit.message",
                "An error occurred while opening the edit at {route}: {e}",
                route=route,
                e=e,
            ),
        )
    return e


def follow_list_route(ctx: "QtContext", route: Union[None, str]):
    if route is None:
        return None
    e = ctx.router.route(route)
    if isinstance(e, Exception):
        ctx.show_error(
            title=ctx.t("router.open-list.title", "Error opening list"),
            message=ctx.t(
                "router.open-list.message",
                "An error occurred while opening the list at {route}: {e}",
                route=route,
                e=e,
            ),
        )
    return e


def follow_create_route(ctx: "QtContext", route: Union[None, str]):
    if route is None:
        return None
    e = ctx.router.route(route)
    if isinstance(e, Exception):
        ctx.show_error(
            title=ctx.t("router.open-create.title", "Error opening create"),
            message=ctx.t(
                "router.open-create.message",
                "An error occurred while opening the create at {route}: {e}",
                route=route,
                e=e,
            ),
        )
    return e


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
        self.triggered.connect(self.do_open)  # type: ignore
        if isinstance(menu_or_parent, QMenu):
            menu_or_parent.addAction(self)
        if icon is not None:
            self.setIcon(icon)

    def do_open(self):
        """Execute the action."""
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
        return result


class OpenListAc(AcBase):
    """Action to open a list of a model."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setIcon(self.get_icon("application_view_list"))

    def do_open(self):
        """Open the list of the model."""
        return follow_list_route(
            ctx=self.ctx,
            route=self.route,
        )


class OpenCreateAc(AcBase):
    """Action to open an editor that allows creating a new record."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setIcon(self.get_icon("document_empty"))

    def do_open(self):
        """Create a new record."""
        return follow_create_route(
            ctx=self.ctx,
            route=self.route,
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
    the record to be edited.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setIcon(self.get_icon("edit_button"))

    def do_open(self):
        """Edit a record."""
        return follow_edit_route(
            ctx=self.ctx,
            route=f"{self.route}/{self.str_id}/edit",
        )


class OpenViewAc(AcBaseWithId):
    """Action to open a viewer that presents a record.

    You can either provide wither the ID or a function that returns the ID of
    the record to be viewed.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setIcon(self.get_icon("eye"))

    def do_open(self):
        """View a record."""
        return follow_view_route(
            ctx=self.ctx,
            route=f"{self.route}/{self.str_id}",
        )


class OpenDeleteAc(AcBaseWithId):
    """Action to open a dialog that allows deleting a record.

    You can either provide wither the ID or a function that returns the ID of
    the record to be deleted.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setIcon(self.get_icon("cross"))

    def do_open(self):
        """Delete a record."""
        return follow_del_route(
            ctx=self.ctx,
            route=f"{self.route}/{self.str_id}/delete",
        )


class RouteProvider:
    """Mixin class that we can use to extract the routes from a class."""

    def get_current_record_selector(self) -> Union[None, "Select"]:
        """Get the selector for the current record."""
        raise NotImplementedError(
            "get_current_record_selector must be implemented in subclasses"
        )

    def get_deletion_function(
        self,
    ) -> Union[None, Callable[[Any, "Session"], bool]]:
        """Get the function to use to delete the record."""
        raise NotImplementedError(
            "get_deletion_function must be implemented in subclasses"
        )

    def get_list_route(self) -> Union[None, str]:
        """Get the route to the list view for this resource."""
        raise NotImplementedError(
            "get_list_route must be implemented in subclasses"
        )

    def get_create_route(self) -> Union[None, str]:
        """Get the route to the create view for this resource."""
        raise NotImplementedError(
            "get_create_route must be implemented in subclasses"
        )

    def get_edit_route(self) -> Union[None, str]:
        """Get the route to the edit view for this resource."""
        raise NotImplementedError(
            "get_edit_route must be implemented in subclasses"
        )

    def get_view_route(self) -> Union[None, str]:
        """Get the route to the view for this resource."""
        raise NotImplementedError(
            "get_view_route must be implemented in subclasses"
        )

    def get_delete_route(self) -> Union[None, str]:
        """Get the route to the delete view for this resource."""
        raise NotImplementedError(
            "get_delete_route must be implemented in subclasses"
        )


class AcProviderBase(QAction, QtUseContext):
    """Base class for all actions that use a provider."""

    provider: RouteProvider

    def __init__(
        self,
        label: str,
        ctx: "QtContext",
        provider: RouteProvider,
        menu_or_parent: Optional[QMenu] = None,
        icon: Optional[QIcon] = None,
    ):
        super().__init__(label, parent=menu_or_parent)
        self.ctx = ctx
        self.provider = provider
        self.triggered.connect(self.do_open)
        if isinstance(menu_or_parent, QMenu):
            menu_or_parent.addAction(self)
        if icon is not None:
            self.setIcon(icon)

    def do_open(self):
        """Execute the action."""
        raise NotImplementedError("do_open must be implemented in subclasses")


class OpenListPac(AcProviderBase):
    """Open the list view for a resource."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setIcon(self.get_icon("application_view_list"))

    def do_open(self):
        return follow_list_route(
            ctx=self.ctx,
            route=self.provider.get_list_route(),
        )


class OpenEditPac(AcProviderBase):
    """Open the edit view for a resource."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setIcon(self.get_icon("edit_button"))

    def do_open(self):
        return follow_edit_route(
            ctx=self.ctx,
            route=self.provider.get_edit_route(),
        )


class OpenCreatePac(AcProviderBase):
    """Open the create view for a resource."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setIcon(self.get_icon("document_empty"))

    def do_open(self):
        return follow_create_route(
            ctx=self.ctx,
            route=self.provider.get_create_route(),
        )


class OpenViewPac(AcProviderBase):
    """Open the view for a resource."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setIcon(self.get_icon("eye"))

    def do_open(self):
        return follow_view_route(
            ctx=self.ctx,
            route=self.provider.get_view_route(),
        )


class OpenDeletePac(AcProviderBase):
    """Open the delete view for a resource."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setIcon(self.get_icon("cross"))

    def do_open(self):
        return follow_del_route(
            ctx=self.ctx,
            route=self.provider.get_delete_route(),
            selectors=self.provider.get_current_record_selector(),
        )
