import logging
from typing import TYPE_CHECKING, Union

from exdrf.field_types.api import (
    BoolField,
    DateTimeField,
    IntField,
    RefManyToManyField,
    RefOneToManyField,
    RefOneToOneField,
    StrField,
)
from exdrf_qt.controls.templ_viewer.templ_viewer import RecordTemplViewer
from exdrf_qt.controls.templ_viewer.view_page import WebEnginePage
from sqlalchemy import select

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy.orm import Session  # noqa: F401

    from exdrf_dev.db.api import Parent as Parent  # noqa: F401

logger = logging.getLogger(__name__)


class QtParentTv(RecordTemplViewer):
    """Template viewer for a Parent database record."""

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.db.api import Parent as DbParent

        super().__init__(
            db_model=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.parents.tv.model",
                DbParent,
            ),
            template_src=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.parents.tv.template",
                "exdrf_dev.qt_gen/db/parents/widgets/parent_tv.html",
            ),
            page_class=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.parents.tv.page_class",
                ctx.get_ovr(
                    "tv.page_class",
                    WebEnginePage,
                ),
            ),
            ctx=ctx,
            **kwargs,
        )
        self.setWindowTitle(
            self.t("parent.tv.title", "Parent viewer"),
        )

    def read_record(self, session: "Session") -> Union[None, "Parent"]:
        from .db.parent import parent_label

        result = session.scalar(
            select(self.db_model).where(
                self.db_model.id == self.record_id,  # type: ignore
            )
        )

        if result is None:
            label = self.t(
                "parent.tv.title-not-found",
                f"Parent - record {self.record_id} not found",
            )
            return None
        else:
            try:
                label = self.t(
                    "parent.tv.title-found",
                    "Parent: view {name}",
                    name=parent_label(result),
                )
            except Exception as e:
                logger.error("Error getting label: %s", e, exc_info=True)
                label = "Parent viewer"

        self.ctx.set_window_title(self, label)
        return result

    def _populate_from_record(self, record: "Parent"):
        self.model.var_bag.add_fields(
            [
                (
                    RefOneToManyField(
                        name="children",
                        title="Children",
                    ),
                    record.children,
                ),
                (
                    DateTimeField(
                        name="created_at",
                        title="Created At",
                        description="Timestamp when the parent was created.",
                    ),
                    record.created_at,
                ),
                (
                    BoolField(
                        name="is_active",
                        title="Is Active",
                        description="Flag indicating if the parent is active.",
                    ),
                    record.is_active,
                ),
                (
                    StrField(
                        name="name",
                        title="Name",
                        description="Name of the parent.",
                    ),
                    record.name,
                ),
                (
                    RefOneToOneField(
                        name="profile",
                        title="Profile",
                    ),
                    record.profile,
                ),
                (
                    RefManyToManyField(
                        name="tags",
                        title="Tags",
                    ),
                    record.tags,
                ),
                (
                    IntField(
                        name="id",
                        title="Id",
                        description="Primary key for the parent.",
                    ),
                    record.id,
                ),
            ]
        )
