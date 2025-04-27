# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.

from typing import TYPE_CHECKING, Union

from exdrf.constants import RecIdType
from exdrf_qt.widgets import EditorDb

from exdrf_dev.qt.composite_key_models.widgets.composite_key_models_editor_ui import (
    Ui_QtCompositeKeyModelEditor,
)

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy.orm import Session  # noqa: F401

    from exdrf_dev.db.models import CompositeKeyModel  # noqa: F401


class QtCompositeKeyModelEditor(
    EditorDb["CompositeKeyModel"], Ui_QtCompositeKeyModelEditor
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
    ) -> "CompositeKeyModel":
        return session.scalar(
            self.selection.where(
                self.db_model.id == record_id  # type: ignore[operator]
            )
        )

    def populate(self, record: Union["CompositeKeyModel", None]):
        pass

    def save_to_record(
        self, record: "CompositeKeyModel", is_new: bool, session: "Session"
    ):
        pass

    def get_id_of_record(self, record: "CompositeKeyModel") -> RecIdType:
        return record.id
