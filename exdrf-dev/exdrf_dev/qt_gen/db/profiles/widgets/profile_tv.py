from typing import TYPE_CHECKING

from exdrf.field_types.api import (
    IntField,
    RefOneToOneField,
    StrField,
)
from exdrf_qt.controls.templ_viewer.templ_viewer import RecordTemplViewer
from sqlalchemy import select

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from exdrf_dev.db.api import Profile as Profile


class QtProfileTv(RecordTemplViewer):
    """Template viewer for a Profile database record."""

    def __init__(self, **kwargs):
        from exdrf_dev.db.api import Profile as DbProfile

        super().__init__(
            db_model=DbProfile, template_src="profile_tv.html", **kwargs
        )

    def read_record(self, session: "Session") -> "Profile":
        return session.scalar(
            select(self.db_model).where(
                self.db_model.id == self.record_id,  # type: ignore[operator]
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
