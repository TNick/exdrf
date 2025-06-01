from typing import TYPE_CHECKING, Union

from exdrf.field_types.api import (
    IntField,
    RefManyToOneField,
    StrField,
)
from exdrf_qt.controls.templ_viewer.templ_viewer import RecordTemplViewer
from exdrf_qt.controls.templ_viewer.view_page import WebEnginePage
from sqlalchemy import select

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy.orm import Session  # noqa: F401

    from exdrf_dev.db.api import Child as Child  # noqa: F401


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
            ctx=ctx,
            **kwargs,
        )

    def read_record(self, session: "Session") -> Union[None, "Child"]:
        return session.scalar(
            select(self.db_model).where(
                self.db_model.id == self.record_id,  # type: ignore
            )
        )

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
