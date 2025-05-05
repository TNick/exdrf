# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.

from typing import TYPE_CHECKING, Union

from exdrf.constants import RecIdType
from exdrf_qt.controls.base_editor import EditorDb

from exdrf_dev.qt.children.widgets.children_editor_ui import Ui_QtChildEditor

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy.orm import Session  # noqa: F401

    from exdrf_dev.db.models import Child  # noqa: F401


class QtChildEditor(EditorDb["Child"], Ui_QtChildEditor):
    """A widget that allows the user to edit a Child record."""

    def __init__(self, ctx: "QtContext", **kwargs):
        """Initialize the editor widget."""
        from exdrf_dev.db.models import Child as DbChild

        super().__init__(ctx=ctx, db_model=DbChild, **kwargs)
        self.verticalLayout.addWidget(self.create_button_box())

    def editing_changed(self, value: bool):
        pass

    def read_record(self, session: "Session", record_id: RecIdType) -> "Child":
        return session.scalar(
            self.selection.where(
                self.db_model.id == record_id  # type: ignore[operator]
            )
        )

    def populate(self, record: Union["Child", None]):
        self.c_id.setText(str(record.id) if record else "")
        super().populate(record)

    def get_id_of_record(self, record: "Child") -> RecIdType:
        return record.id
