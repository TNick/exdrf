from typing import TYPE_CHECKING

from exdrf.field_types.api import (
    BlobField,
    DateField,
    EnumField,
    FloatField,
    FormattedField,
    IntField,
    RefOneToManyField,
    StrField,
    TimeField,
)
from exdrf_qt.controls.templ_viewer.templ_viewer import RecordTemplViewer
from sqlalchemy import select

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from exdrf_dev.db.api import CompositeKeyModel as CompositeKeyModel


class QtCompositeKeyModelTv(RecordTemplViewer):
    """Template viewer for a CompositeKeyModel database record."""

    def __init__(self, **kwargs):
        from exdrf_dev.db.api import CompositeKeyModel as DbCompositeKeyModel

        super().__init__(
            db_model=DbCompositeKeyModel,
            template_src="composite_key_model_tv.html",
            **kwargs,
        )

    def read_record(self, session: "Session") -> "CompositeKeyModel":
        return session.scalar(
            select(self.db_model).where(
                self.db_model.key_part1 == self.record_id[0],  # type: ignore[operator]
                self.db_model.key_part2 == self.record_id[1],  # type: ignore[operator]
            )
        )

    def _populate_from_record(self, record: "CompositeKeyModel"):
        self.model.var_bag.add_fields(
            [
                (
                    StrField(
                        name="description",
                        title="Description",
                        description="A description for this record.",
                    ),
                    record.description,
                ),
                (
                    RefOneToManyField(
                        name="related_items",
                        title="Related Items",
                    ),
                    record.related_items,
                ),
                (
                    BlobField(
                        name="some_binary",
                        title="Some Binary",
                        description="Binary data.",
                    ),
                    record.some_binary,
                ),
                (
                    DateField(
                        name="some_date",
                        title="Some Date",
                        description="A date value.",
                    ),
                    record.some_date,
                ),
                (
                    EnumField(
                        name="some_enum",
                        title="Some Enum",
                        description="An enum value representing status.",
                    ),
                    record.some_enum,
                ),
                (
                    FloatField(
                        name="some_float",
                        title="Some Float",
                        description="A floating-point number.",
                    ),
                    record.some_float,
                ),
                (
                    FormattedField(
                        name="some_json",
                        title="Some Json",
                        description="A JSON object.",
                    ),
                    record.some_json,
                ),
                (
                    TimeField(
                        name="some_time",
                        title="Some Time",
                        description="A time value.",
                    ),
                    record.some_time,
                ),
                (
                    StrField(
                        name="key_part1",
                        title="Key Part1",
                        description="First part of the composite primary key (string).",
                    ),
                    record.key_part1,
                ),
                (
                    IntField(
                        name="key_part2",
                        title="Key Part2",
                        description="Second part of the composite primary key (integer).",
                    ),
                    record.key_part2,
                ),
            ]
        )
