from typing import TYPE_CHECKING, Union

from exdrf.field_types.api import (
    DateField,
    EnumField,
    FloatField,
    IntField,
    RefOneToManyField,
    StrField,
    TimeField,
)
from exdrf_qt.controls.templ_viewer.templ_viewer import RecordTemplViewer
from sqlalchemy import select

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy.orm import Session  # noqa: F401

    from exdrf_dev.db.api import (
        CompositeKeyModel as CompositeKeyModel,
    )  # noqa: F401


class QtCompositeKeyModelTv(RecordTemplViewer):
    """Template viewer for a CompositeKeyModel database record."""

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.db.api import CompositeKeyModel as DbCompositeKeyModel

        super().__init__(
            db_model=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.composite_key_models.tv.model",
                DbCompositeKeyModel,
            ),
            template_src=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.composite_key_models.tv.template",
                "exdrf_dev.qt_gen/db/composite_key_models/widgets/composite_key_model_tv.html",
            ),
            ctx=ctx,
            **kwargs,
        )

    def read_record(
        self, session: "Session"
    ) -> Union[None, "CompositeKeyModel"]:
        return session.scalar(
            select(self.db_model).where(
                self.db_model.key_part1 == self.record_id[0],  # type: ignore
                self.db_model.key_part2 == self.record_id[1],  # type: ignore
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
