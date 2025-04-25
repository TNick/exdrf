# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.

from typing import TYPE_CHECKING, Union

from exdrf.constants import RecIdType
from exdrf_qt.widgets import EditorDb

from exdrf_dev.qt.related_items.widgets.related_items_editor_ui import (
    Ui_QtRelatedItemEditor,
)

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy.orm import Session  # noqa: F401

    from exdrf_dev.db.models import RelatedItem  # noqa: F401


class QtRelatedItemEditor(EditorDb["RelatedItem"], Ui_QtRelatedItemEditor):
    """A widget that allows the user to edit a RelatedItem record."""

    def __init__(self, ctx: "QtContext", **kwargs):
        """Initialize the editor widget."""
        from exdrf_dev.db.models import RelatedItem as DbRelatedItem

        super().__init__(ctx=ctx, db_model=DbRelatedItem, **kwargs)
        self.setup_ui(self)

    def editing_changed(self, value: bool):
        pass

    def read_record(
        self, session: "Session", record_id: RecIdType
    ) -> "RelatedItem":
        return session.scalar(
            self.selection.where(
                self.db_model.id == record_id  # type: ignore[operator]
            )
        )

    def populate(self, record: Union["RelatedItem", None]):
        pass

    def save_to_record(
        self, record: "RelatedItem", is_new: bool, session: "Session"
    ):
        pass

    def get_id_of_record(self, record: "RelatedItem") -> RecIdType:
        return record.id
