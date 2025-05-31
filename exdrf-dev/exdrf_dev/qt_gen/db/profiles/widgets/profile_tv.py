from typing import TYPE_CHECKING, Union

from exdrf.field_types.api import (
    IntField,
    RefOneToOneField,
    StrField,
)
from exdrf_qt.controls.templ_viewer.templ_viewer import RecordTemplViewer
from sqlalchemy import select

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy.orm import Session  # noqa: F401

    from exdrf_dev.db.api import Profile as Profile  # noqa: F401


class QtProfileTv(RecordTemplViewer):
    """Template viewer for a Profile database record."""

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.db.api import Profile as DbProfile

        super().__init__(
            db_model=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.profiles.tv.model",
                DbProfile,
            ),
            template_src=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.profiles.tv.template",
                "exdrf_dev.qt_gen/db/profiles/widgets/profile_tv.html",
            ),
            ctx=ctx,
            **kwargs,
        )

    def read_record(self, session: "Session") -> Union[None, "Profile"]:
        return session.scalar(
            select(self.db_model).where(
                self.db_model.id == self.record_id,  # type: ignore
            )
        )

    def _populate_from_record(self, record: "Profile"):
        self.model.var_bag.add_fields(
            [
                (
                    StrField(
                        name="bio",
                        title="Bio",
                        description="Biography text for the profile.",
                    ),
                    record.bio,
                ),
                (
                    RefOneToOneField(
                        name="parent",
                        title="Parent",
                    ),
                    record.parent,
                ),
                (
                    IntField(
                        name="parent_id",
                        title="Parent Id",
                        description="Foreign key linking to the parent (must be unique).",
                    ),
                    record.parent_id,
                ),
                (
                    IntField(
                        name="id",
                        title="Id",
                        description="Primary key for the profile.",
                    ),
                    record.id,
                ),
            ]
        )
