import logging
from typing import TYPE_CHECKING, Any, Callable, Union

from exdrf.constants import RecIdType
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
from exdrf_qt.controls.templ_viewer.view_page import WebEnginePage
from exdrf_qt.plugins import exdrf_qt_pm, safe_hook_call
from sqlalchemy import Select, select

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy.orm import Session  # noqa: F401

    from exdrf_dev.db.api import (
        CompositeKeyModel as CompositeKeyModel,
    )  # noqa: F401

logger = logging.getLogger(__name__)


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
            page_class=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.composite_key_models.tv.page_class",
                ctx.get_ovr(
                    "tv.page_class",
                    WebEnginePage,
                ),
            ),
            other_actions=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.composite_key_models.tv.extra-menus", None
            ),
            ctx=ctx,
            **kwargs,
        )
        if not self.windowTitle():
            self.setWindowTitle(
                self.t(
                    "composite_key_model.tv.title", "Composite key model viewer"
                ),
            )

        # Inform plugins that the viewer has been created.
        safe_hook_call(
            exdrf_qt_pm.hook.composite_key_model_tv_created, widget=self
        )

    def read_record(
        self, session: "Session"
    ) -> Union[None, "CompositeKeyModel"]:
        from .db.composite_key_model import composite_key_model_label

        result = session.scalar(
            select(self.db_model).where(
                self.db_model.key_part1 == self.record_id[0],  # type: ignore
                self.db_model.key_part2 == self.record_id[1],  # type: ignore
            )
        )

        if result is None:
            label = self.t(
                "composite_key_model.tv.title-not-found",
                f"Composite key model - record {self.record_id} not found",
            )
            return None
        else:
            try:
                label = self.t(
                    "composite_key_model.tv.title-found",
                    "Composite key model: view {name}",
                    name=composite_key_model_label(result),
                )
            except Exception as e:
                logger.error("Error getting label: %s", e, exc_info=True)
                label = "Composite key model viewer"

        self.ctx.set_window_title(self, label)
        return result

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

    def get_db_item_id(self, record: "CompositeKeyModel") -> RecIdType:
        return (
            record.key_part1,
            record.key_part2,
        )

    def get_current_record_selector(self) -> Union[None, "Select"]:
        if self.record_id is None:
            return None
        return select(self.db_model).where(
            self.db_model.key_part1 == self.record_id[0],  # type: ignore
            self.db_model.key_part2 == self.record_id[1],  # type: ignore
        )

    def get_deletion_function(
        self,
    ) -> Union[None, Callable[[Any, "Session"], bool]]:
        from exdrf_qt.utils.router import session_del_record

        return session_del_record
