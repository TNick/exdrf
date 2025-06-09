import logging
from typing import TYPE_CHECKING, Any, Callable, Union

from exdrf.constants import RecIdType
from exdrf.field_types.api import (
    IntField,
    RefManyToOneField,
    StrField,
)
from exdrf_qt.controls.templ_viewer.templ_viewer import RecordTemplViewer
from exdrf_qt.controls.templ_viewer.view_page import WebEnginePage
from sqlalchemy import Select, select

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy.orm import Session  # noqa: F401

    from exdrf_dev.db.api import Child as Child  # noqa: F401

logger = logging.getLogger(__name__)


class QtChildTv(RecordTemplViewer):
    """Template viewer for a Child database record."""

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.db.api import Child as DbChild

        super().__init__(
            db_model=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.children.tv.model",
                DbChild,
            ),
            template_src=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.children.tv.template",
                "exdrf_dev.qt_gen/db/children/widgets/child_tv.html",
            ),
            page_class=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.children.tv.page_class",
                ctx.get_ovr(
                    "tv.page_class",
                    WebEnginePage,
                ),
            ),
            other_actions=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.children.tv.extra-menus", None
            ),
            ctx=ctx,
            **kwargs,
        )
        if not self.windowTitle():
            self.setWindowTitle(
                self.t("child.tv.title", "Child viewer"),
            )

    def read_record(self, session: "Session") -> Union[None, "Child"]:
        from .db.child import child_label

        result = session.scalar(
            select(self.db_model).where(
                self.db_model.id == self.record_id,  # type: ignore
            )
        )

        if result is None:
            label = self.t(
                "child.tv.title-not-found",
                f"Child - record {self.record_id} not found",
            )
            return None
        else:
            try:
                label = self.t(
                    "child.tv.title-found",
                    "Child: view {name}",
                    name=child_label(result),
                )
            except Exception as e:
                logger.error("Error getting label: %s", e, exc_info=True)
                label = "Child viewer"

        self.ctx.set_window_title(self, label)
        return result

    def _populate_from_record(self, record: "Child"):
        self.model.var_bag.add_fields(
            [
                (
                    StrField(
                        name="data",
                        title="Data",
                        description="Some data associated with the child.",
                    ),
                    record.data,
                ),
                (
                    RefManyToOneField(
                        name="parent",
                        title="Parent",
                    ),
                    record.parent,
                ),
                (
                    IntField(
                        name="parent_id",
                        title="Parent Id",
                        description="Foreign key linking to the parent.",
                    ),
                    record.parent_id,
                ),
                (
                    IntField(
                        name="id",
                        title="Id",
                        description="Primary key for the child.",
                    ),
                    record.id,
                ),
            ]
        )

    def get_db_item_id(self, record: "Child") -> RecIdType:
        return record.id

    def get_current_record_selector(self) -> Union[None, "Select"]:
        if self.record_id is None:
            return None
        return select(self.db_model).where(
            self.db_model.id == self.record_id,  # type: ignore
        )

    def get_deletion_function(
        self,
    ) -> Union[None, Callable[[Any, "Session"], bool]]:
        return lambda rec, session: session.delete(rec)  # type: ignore
