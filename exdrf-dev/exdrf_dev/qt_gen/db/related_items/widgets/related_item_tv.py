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

    from exdrf_dev.db.api import RelatedItem as RelatedItem


class QtRelatedItemTv(RecordTemplViewer):
    """Template viewer for a RelatedItem database record."""

    def __init__(self, **kwargs):
        from exdrf_dev.db.api import RelatedItem as DbRelatedItem

        super().__init__(
            db_model=DbRelatedItem,
            template_src="related_item_tv.html",
            **kwargs,
        )

    def read_record(self, session: "Session") -> "RelatedItem":
        return session.scalar(
            select(self.db_model).where(
                self.db_model.id == self.record_id,  # type: ignore[operator]
            )
        )

    def _populate_from_record(self, record: "RelatedItem"):
        self.model.var_bag.add_fields(
            [
                (
                    RefManyToOneField(
                        name="comp_key_owner",
                        title="Comp Key Owner",
                    ),
                    record.comp_key_owner,
                ),
                (
                    StrField(
                        name="comp_key_part1",
                        title="Comp Key Part1",
                        description="Foreign key part 1 referencing CompositeKeyModel.",
                    ),
                    record.comp_key_part1,
                ),
                (
                    IntField(
                        name="comp_key_part2",
                        title="Comp Key Part2",
                        description="Foreign key part 2 referencing CompositeKeyModel.",
                    ),
                    record.comp_key_part2,
                ),
                (
                    StrField(
                        name="item_data",
                        title="Item Data",
                        description="Data specific to the related item.",
                    ),
                    record.item_data,
                ),
                (
                    IntField(
                        name="some_int",
                        title="Some Int",
                        description="An integer value associated with the related item.",
                    ),
                    record.some_int,
                ),
                (
                    IntField(
                        name="id",
                        title="Id",
                        description="Primary key for the related item.",
                    ),
                    record.id,
                ),
            ]
        )
