from typing import TYPE_CHECKING

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
from sqlalchemy import select

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from exdrf_dev.db.api import Parent as Parent


class QtParentTv(RecordTemplViewer):
    """Template viewer for a Parent database record."""

    def __init__(self, **kwargs):
        from exdrf_dev.db.api import Parent as DbParent

        super().__init__(
            db_model=DbParent, template_src="parent_tv.html", **kwargs
        )

    def read_record(self, session: "Session") -> "Parent":
        return session.scalar(
            select(self.db_model).where(
                self.db_model.id == self.record_id,  # type: ignore[operator]
            )
        )

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
