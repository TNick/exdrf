import logging
from typing import TYPE_CHECKING, Any, Callable, Union

from exdrf.constants import RecIdType
from exdrf.field_types.api import (
    IntField,
    RefManyToOneField,
    StrField,
)
from exdrf_qt.controls.templ_viewer.templ_viewer import RecordTemplViewer
from exdrf_qt.controls.templ_viewer.view_page import WebEnginePage
from sqlalchemy import Select, select

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy.orm import Session  # noqa: F401

    from exdrf_dev.db.api import RelatedItem as RelatedItem  # noqa: F401

logger = logging.getLogger(__name__)


class QtRelatedItemTv(RecordTemplViewer):
    """Template viewer for a RelatedItem database record."""

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.db.api import RelatedItem as DbRelatedItem

        super().__init__(
            db_model=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.related_items.tv.model",
                DbRelatedItem,
            ),
            template_src=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.related_items.tv.template",
                "exdrf_dev.qt_gen/db/related_items/widgets/related_item_tv.html",
            ),
            page_class=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.related_items.tv.page_class",
                ctx.get_ovr(
                    "tv.page_class",
                    WebEnginePage,
                ),
            ),
            other_actions=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.related_items.tv.extra-menus", None
            ),
            ctx=ctx,
            **kwargs,
        )
        if not self.windowTitle():
            self.setWindowTitle(
                self.t("related_item.tv.title", "Related item viewer"),
            )

    def read_record(self, session: "Session") -> Union[None, "RelatedItem"]:
        from .db.related_item import related_item_label

        result = session.scalar(
            select(self.db_model).where(
                self.db_model.id == self.record_id,  # type: ignore
            )
        )

        if result is None:
            label = self.t(
                "related_item.tv.title-not-found",
                f"Related item - record {self.record_id} not found",
            )
            return None
        else:
            try:
                label = self.t(
                    "related_item.tv.title-found",
                    "Related item: view {name}",
                    name=related_item_label(result),
                )
            except Exception as e:
                logger.error("Error getting label: %s", e, exc_info=True)
                label = "Related item viewer"

        self.ctx.set_window_title(self, label)
        return result

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

    def get_db_item_id(self, record: "RelatedItem") -> RecIdType:
        return record.id

    def get_current_record_selector(self) -> Union[None, "Select"]:
        if self.record_id is None:
            return None
        return select(self.db_model).where(
            self.db_model.id == self.record_id,  # type: ignore
        )

    def get_deletion_function(
        self,
    ) -> Union[None, Callable[[Any, Session], bool]]:
        return lambda rec, session: session.delete(rec)  # type: ignore
