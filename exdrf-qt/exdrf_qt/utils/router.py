import logging
from operator import and_
from typing import TYPE_CHECKING, Any, Callable, List, Union

from attrs import define, field
from parse import compile as parse_compile
from PyQt5.QtWidgets import QMessageBox
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401

logger = logging.getLogger(__name__)


def default_del_record(record: Any, session: Session):
    record.deleted = True
    return True


@define
class Route:
    """A route is a pattern and a handler.

    Attributes:
        pattern: The pattern to match the path.
        handler: The function to call when the path is matched.
        parser: The parser for the pattern.
        segment_count: The number of segments in the pattern.
    """

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

    def route(self, path: str, **kwargs) -> Any:
        """Route a path to a handler.

        You can provide additional parameters that will be passed to the
        handler.
        """
        for route in self.routes:
            result = route.match(path)
            if result:
                params = {
                    **kwargs,
                    **result.named,
                }
                try:
                    route.handler(self, *result.fixed, **params)
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

    def open_viewer(self, viewer_class, id: Any = None):
        """Open the list of the model."""
        try:
            if not self.ctx.ensure_db_conn():
                return
            w = viewer_class(
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

    def delete_record(
        self,
        record_class,
        id: Any = None,
        selectors: Union[List[Any], Select, None] = None,
        perform_deletion: Callable[[Any, Session], bool] = default_del_record,
    ):
        """Delete a record from the model.

        Args:
            record_class: The class of the record to delete.
            id: The id of the record to delete.
            selectors: The selectors to use to delete the record. Can be a
                prepared SQLAlchemy select statement which will be used
                directly, a list of ORM columns which will be used to build
                a select statement together with record_class and the record
                id, or None if the model has an single primary key called id.
            perform_deletion: The function to use to perform the deletion.

        Returns:
            True if the record was deleted, False otherwise.
        """
        if id is None:
            logger.error("No id provided for deletion")
            return False

        select_stm = None
        if isinstance(selectors, Select):
            select_stm = selectors
        elif selectors is not None and len(selectors) > 0:
            if isinstance(id, (int, str)):
                id = [id]
            if len(selectors) != len(id):
                # Not an error message because this is a programmer error.
                raise ValueError(
                    "The number of selectors must be the same as the number "
                    "of ids"
                )
            select_stm = select(record_class).where(
                and_(*[selector == id_ for selector, id_ in zip(selectors, id)])
            )
        elif not hasattr(record_class, "id") or not hasattr(
            record_class, "deleted"
        ):
            QMessageBox.critical(
                self.ctx.top_widget,
                self.t(
                    "cmn.delete-record.title",
                    "Deleting record {rec}",
                    rec=str(id),
                ),
                self.t(
                    "cmn.delete-record.cannot-id-deleted",
                    "Record class {cls} must have id and deleted fields",
                    cls=record_class.__name__,
                ),
                QMessageBox.Ok,
            )
            return False
        else:
            select_stm = select(record_class).where(record_class.id == id)

        if perform_deletion is None and not hasattr(record_class, "deleted"):
            QMessageBox.critical(
                self.ctx.top_widget,
                self.t(
                    "cmn.delete-record.title",
                    "Deleting record {rec}",
                    rec=str(id),
                ),
                self.t(
                    "cmn.delete-record.cannot-deleted",
                    "Record class {cls} must have a field called `deleted`",
                    cls=record_class.__name__,
                ),
                QMessageBox.Ok,
            )
            return False

        reply = QMessageBox.question(
            self.ctx.top_widget,
            self.t(
                "cmn.delete-record.title",
                "Deleting record {rec}",
                rec=str(id),
            ),
            self.t(
                "cmn.delete-record.message",
                "Are you sure you want to delete this record?",
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return False

        try:
            with self.ctx.same_session() as session:
                record = session.scalar(select_stm)
                if record is None:
                    return
                if not perform_deletion(record, session):
                    return
                session.commit()
                return True
        except Exception as e:
            logger.error("Error deleting record", exc_info=True)
            QMessageBox.warning(
                self.ctx.top_widget,
                self.t(
                    "cmn.delete-record.title",
                    "Deleting record {rec}",
                    rec=str(id),
                ),
                self.t(
                    "cmn.delete-record.failed",
                    "An error occurred while deleting the record: {e}",
                    e=e,
                ),
            )
            return False
