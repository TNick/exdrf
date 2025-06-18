import logging
from typing import TYPE_CHECKING, Any, Callable, Union

from exdrf.constants import RecIdType
from exdrf.field_types.api import (
    IntField,
    RefManyToManyField,
    StrField,
)
from exdrf_qt.controls.templ_viewer.templ_viewer import RecordTemplViewer
from exdrf_qt.controls.templ_viewer.view_page import WebEnginePage
from exdrf_qt.plugins import exdrf_qt_pm, safe_hook_call
from sqlalchemy import Select, select

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy.orm import Session  # noqa: F401

    from exdrf_dev.db.api import Tag as Tag  # noqa: F401

logger = logging.getLogger(__name__)


class QtTagTv(RecordTemplViewer):
    """Template viewer for a Tag database record."""

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.db.api import Tag as DbTag

        super().__init__(
            db_model=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.tags.tv.model",
                DbTag,
            ),
            template_src=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.tags.tv.template",
                "exdrf_dev.qt_gen/db/tags/widgets/tag_tv.html",
            ),
            page_class=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.tags.tv.page_class",
                ctx.get_ovr(
                    "tv.page_class",
                    WebEnginePage,
                ),
            ),
            other_actions=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.tags.tv.extra-menus", None
            ),
            ctx=ctx,
            **kwargs,
        )
        if not self.windowTitle():
            self.setWindowTitle(
                self.t("tag.tv.title", "Tag viewer"),
            )

        # Inform plugins that the viewer has been created.
        safe_hook_call(exdrf_qt_pm.hook.tag_tv_created, widget=self)

    def read_record(self, session: "Session") -> Union[None, "Tag"]:
        from .db.tag import tag_label

        result = session.scalar(
            select(self.db_model).where(
                self.db_model.id == self.record_id,  # type: ignore
            )
        )

        if result is None:
            label = self.t(
                "tag.tv.title-not-found",
                f"Tag - record {self.record_id} not found",
            )
            return None
        else:
            try:
                label = self.t(
                    "tag.tv.title-found",
                    "Tag: view {name}",
                    name=tag_label(result),
                )
            except Exception as e:
                logger.error("Error getting label: %s", e, exc_info=True)
                label = "Tag viewer"

        self.ctx.set_window_title(self, label)
        return result

    def _populate_from_record(self, record: "Tag"):
        self.model.var_bag.add_fields(
            [
                (
                    StrField(
                        name="name",
                        title="Name",
                        description="Unique name of the tag.",
                    ),
                    record.name,
                ),
                (
                    RefManyToManyField(
                        name="parents",
                        title="Parents",
                    ),
                    record.parents,
                ),
                (
                    IntField(
                        name="id",
                        title="Id",
                        description="Primary key for the tag.",
                    ),
                    record.id,
                ),
            ]
        )

    def get_db_item_id(self, record: "Tag") -> RecIdType:
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
        from exdrf_qt.utils.router import session_del_record

        return session_del_record
