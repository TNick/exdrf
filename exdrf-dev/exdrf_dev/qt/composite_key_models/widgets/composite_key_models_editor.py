# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.

from typing import TYPE_CHECKING, Union, cast

from sqlalchemy import select

from exdrf.constants import RecIdType
from exdrf_dev.qt.composite_key_models.widgets.composite_key_models_editor_ui import (
    Ui_QtCompositeKeyModelEditor,
)
from exdrf_qt.controls.base_editor import ExdrfEditor

if TYPE_CHECKING:
    from sqlalchemy.orm import Session  # noqa: F401

    from exdrf_dev.db.models import CompositeKeyModel  # noqa: F401
    from exdrf_qt.context import QtContext  # noqa: F401


class QtCompositeKeyModelEditor(
    ExdrfEditor["CompositeKeyModel"], Ui_QtCompositeKeyModelEditor
):
    """A widget that allows the user to edit a CompositeKeyModel record."""

    def __init__(self, ctx: "QtContext", **kwargs):
        """Initialize the editor widget."""
        from exdrf_dev.db.models import CompositeKeyModel as DbCompositeKeyModel

        super().__init__(ctx=ctx, db_model=DbCompositeKeyModel, **kwargs)
        self.setup_ui(self)
        self.verticalLayout.addChildWidget(self.create_button_box())

    def editing_changed(self, value: bool):
        pass

    def read_record(
        self, session: "Session", record_id: RecIdType
    ) -> Union["CompositeKeyModel", None]:
        """Load the CompositeKeyModel row for the structured ``record_id``."""
        if not isinstance(record_id, tuple):
            return None
        if len(record_id) != 2:
            return None

        k1, k2 = record_id

        stmt = select(self.db_model).where(
            self.db_model.key_part1 == k1,
            self.db_model.key_part2 == k2,
        )

        result = session.scalar(stmt)

        if result is None:
            self.ctx.set_window_title(
                self,
                self.t(
                    "composite_key_model.editor.title-not-found",
                    "Composite key model - record missing",
                ),
            )
            return None

        title = self.t(
            "composite_key_model.editor.title-found",
            "Composite key model: ({k1}, {k2})",
            k1=k1,
            k2=k2,
        )
        self.ctx.set_window_title(self, title)
        return cast("CompositeKeyModel", result)

    def populate(self, record: Union["CompositeKeyModel", None]):
        pass

    def save_to_record(
        self, record: "CompositeKeyModel", is_new: bool, session: "Session"
    ):
        pass

    def get_id_of_record(self, record: "CompositeKeyModel") -> RecIdType:
        """Return this table's composite primary key as ``(key_part1, key_part2)``."""
        return (record.key_part1, record.key_part2)
