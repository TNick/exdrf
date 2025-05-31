from typing import TYPE_CHECKING

from exdrf.field_types.api import (
    IntField,
)
from exdrf_qt.controls.templ_viewer.templ_viewer import RecordTemplViewer
from sqlalchemy import select

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from exdrf_dev.db.api import ParentTagAssociation as ParentTagAssociation


class QtParentTagAssociationTv(RecordTemplViewer):
    """Template viewer for a ParentTagAssociation database record."""

    def __init__(self, **kwargs):
        from exdrf_dev.db.api import (
            ParentTagAssociation as DbParentTagAssociation,
        )

        super().__init__(
            db_model=DbParentTagAssociation,
            template_src="parent_tag_association_tv.html",
            **kwargs,
        )

    def read_record(self, session: "Session") -> "ParentTagAssociation":
        return session.scalar(
            select(self.db_model).where(
                self.db_model.parent_id == self.record_id[0],  # type: ignore[operator]
                self.db_model.tag_id == self.record_id[1],  # type: ignore[operator]
            )
        )

    def _populate_from_record(self, record: "ParentTagAssociation"):
        self.model.var_bag.add_fields(
            [
                (
                    IntField(
                        name="parent_id",
                        title="Parent Id",
                        description="Foreign key to the parents table.",
                    ),
                    record.parent_id,
                ),
                (
                    IntField(
                        name="tag_id",
                        title="Tag Id",
                        description="Foreign key to the tags table.",
                    ),
                    record.tag_id,
                ),
            ]
        )
