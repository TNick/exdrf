from typing import TYPE_CHECKING

from exdrf.field_types.api import (
    IntField,
    RefManyToOneField,
    StrField,
)
from exdrf_qt.controls.templ_viewer.templ_viewer import RecordTemplViewer
from sqlalchemy import select

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from exdrf_dev.db.api import Child as Child


class QtChildTv(RecordTemplViewer):
    """Template viewer for a Child database record."""

    def __init__(self, **kwargs):
        from exdrf_dev.db.api import Child as DbChild

        super().__init__(
            db_model=DbChild, template_src="child_tv.html", **kwargs
        )

    def read_record(self, session: "Session") -> "Child":
        return session.scalar(
            select(self.db_model).where(
                self.db_model.id == self.record_id,  # type: ignore[operator]
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
