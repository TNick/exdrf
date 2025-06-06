import logging
from typing import TYPE_CHECKING, Any, Callable, List

from attrs import define, field
from parse import compile as parse_compile

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401

logger = logging.getLogger(__name__)


@define
class Route:
    pattern: str
    handler: Callable[..., Any]
    parser: Any = field(init=False)
    segment_count: int = field(init=False)

    def __attrs_post_init__(self):
        self.parser = parse_compile(self.pattern)
        self.segment_count = self.pattern.count("/")

    def match(self, path: str):
        return self.parser.parse(path)


@define
class ExdrfRouter(QtUseContext):
    """Router for the application."""

    ctx: "QtContext"
    base_path: str
    routes: List[Route] = field(factory=list)

    def __attrs_post_init__(self):
        self.routes.sort(key=lambda r: r.segment_count, reverse=True)

    def add_route(self, pattern: str, handler: Callable):
        """Add a route to the router."""
        full_pattern = self._normalize_pattern(pattern)
        route = Route(full_pattern, handler)
        self.routes.append(route)
        self.routes.sort(key=lambda r: r.segment_count, reverse=True)

    def remove_route(self, pattern: str):
        """Remove a route from the router."""
        full_pattern = self._normalize_pattern(pattern)
        self.routes = [r for r in self.routes if r.pattern != full_pattern]

    def route(self, path: str) -> Any:
        """Route a path to a handler."""
        for route in self.routes:
            result = route.match(path)
            if result:
                try:
                    route.handler(self, *result.fixed, **result.named)
                    return None
                except (ValueError, TypeError) as e:
                    return e
        return ValueError("No matching route found.")

    def _normalize_pattern(self, pattern: str) -> str:
        return self.base_path.rstrip("/") + "/" + pattern.lstrip("/")

    def open_editor(self, editor_class, id: Any = None):
        """Open the editor of the model."""
        try:
            if not self.ctx.ensure_db_conn():
                return
            w = editor_class(
                ctx=self.ctx,
                record_id=id,
            )
            if id is None:
                w.on_create_new()
            else:
                w.on_begin_edit()
            self.ctx.create_window(w, w.windowTitle())
        except Exception as e:
            logger.error("Error opening list", exc_info=True)
            self.ctx.show_error(
                title=self.t("cmn.open-list.title", "Error opening list"),
                message=self.t(
                    "cmn.open-list.message",
                    "An error occurred while opening the list: {e}",
                    e=e,
                ),
            )
            return

    def open_list(self, list_class):
        """Open the list of the model."""
        try:
            if not self.ctx.ensure_db_conn():
                return
            w = list_class(ctx=self.ctx)
            self.ctx.create_window(w, w.windowTitle())
        except Exception as e:
            logger.error("Error opening list", exc_info=True)
            self.ctx.show_error(
                title=self.t("cmn.open-list.title", "Error opening list"),
                message=self.t(
                    "cmn.open-list.message",
                    "An error occurred while opening the list: {e}",
                    e=e,
                ),
            )
            return

    def open_viewer(self, list_class, id: Any = None):
        """Open the list of the model."""
        try:
            if not self.ctx.ensure_db_conn():
                return
            w = list_class(
                ctx=self.ctx,
                record_id=id,
            )
            self.ctx.create_window(w, w.windowTitle())
        except Exception as e:
            logger.error("Error opening list", exc_info=True)
            self.ctx.show_error(
                title=self.t("cmn.open-list.title", "Error opening list"),
                message=self.t(
                    "cmn.open-list.message",
                    "An error occurred while opening the list: {e}",
                    e=e,
                ),
            )
            return

    def delete_record(self, record_class, id: Any = None):
        """Delete a record from the model."""
        raise NotImplementedError("Not implemented")
