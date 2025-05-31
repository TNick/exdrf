from typing import TYPE_CHECKING

from exdrf.field_types.api import (
    IntField,
    RefManyToManyField,
    StrField,
)
from exdrf_qt.controls.templ_viewer.templ_viewer import RecordTemplViewer
from sqlalchemy import select

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from exdrf_dev.db.api import Tag as Tag


class QtTagTv(RecordTemplViewer):
    """Template viewer for a Tag database record."""

    def __init__(self, **kwargs):
        from exdrf_dev.db.api import Tag as DbTag

        super().__init__(db_model=DbTag, template_src="tag_tv.html", **kwargs)

    def read_record(self, session: "Session") -> "Tag":
        return session.scalar(
            select(self.db_model).where(
                self.db_model.id == self.record_id,  # type: ignore[operator]
            )
        )

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
