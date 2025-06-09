import logging
from typing import TYPE_CHECKING, Any, Callable, Union

from exdrf.constants import RecIdType
from exdrf.field_types.api import (
    IntField,
)
from exdrf_qt.controls.templ_viewer.templ_viewer import RecordTemplViewer
from exdrf_qt.controls.templ_viewer.view_page import WebEnginePage
from sqlalchemy import Select, select

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy.orm import Session  # noqa: F401

    from exdrf_dev.db.api import (  # noqa: F401
        ParentTagAssociation as ParentTagAssociation,
    )

logger = logging.getLogger(__name__)


class QtParentTagAssociationTv(RecordTemplViewer):
    """Template viewer for a ParentTagAssociation database record."""

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.db.api import (
            ParentTagAssociation as DbParentTagAssociation,
        )

        super().__init__(
            db_model=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.parent_tag_associations.tv.model",
                DbParentTagAssociation,
            ),
            template_src=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.parent_tag_associations.tv.template",
                "exdrf_dev.qt_gen/db/parent_tag_associations/widgets/parent_tag_association_tv.html",
            ),
            page_class=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.parent_tag_associations.tv.page_class",
                ctx.get_ovr(
                    "tv.page_class",
                    WebEnginePage,
                ),
            ),
            other_actions=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.parent_tag_associations.tv.extra-menus",
                None,
            ),
            ctx=ctx,
            **kwargs,
        )
        if not self.windowTitle():
            self.setWindowTitle(
                self.t(
                    "parent_tag_association.tv.title",
                    "Parent tag association viewer",
                ),
            )

    def read_record(
        self, session: "Session"
    ) -> Union[None, "ParentTagAssociation"]:
        from .db.parent_tag_association import parent_tag_association_label

        result = session.scalar(
            select(self.db_model).where(
                self.db_model.parent_id == self.record_id[0],  # type: ignore
                self.db_model.tag_id == self.record_id[1],  # type: ignore
            )
        )

        if result is None:
            label = self.t(
                "parent_tag_association.tv.title-not-found",
                f"Parent tag association - record {self.record_id} not found",
            )
            return None
        else:
            try:
                label = self.t(
                    "parent_tag_association.tv.title-found",
                    "Parent tag association: view {name}",
                    name=parent_tag_association_label(result),
                )
            except Exception as e:
                logger.error("Error getting label: %s", e, exc_info=True)
                label = "Parent tag association viewer"

        self.ctx.set_window_title(self, label)
        return result

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

    def get_db_item_id(self, record: "ParentTagAssociation") -> RecIdType:
        return (
            record.parent_id,
            record.tag_id,
        )

    def get_current_record_selector(self) -> Union[None, "Select"]:
        if self.record_id is None:
            return None
        return select(self.db_model).where(
            self.db_model.parent_id == self.record_id[0],  # type: ignore
            self.db_model.tag_id == self.record_id[1],  # type: ignore
        )

    def get_deletion_function(
        self,
    ) -> Union[None, Callable[[Any, Session], bool]]:
        return lambda rec, session: session.delete(rec)  # type: ignore
