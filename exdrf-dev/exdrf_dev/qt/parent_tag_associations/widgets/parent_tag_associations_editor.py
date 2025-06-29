# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.

from typing import TYPE_CHECKING, Union

from exdrf.constants import RecIdType
from exdrf_qt.controls.base_editor import ExdrfEditor

from exdrf_dev.qt.parent_tag_associations.widgets.parent_tag_associations_editor_ui import (
    Ui_QtParentTagAssociationEditor,
)

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy.orm import Session  # noqa: F401

    from exdrf_dev.db.models import ParentTagAssociation  # noqa: F401


class QtParentTagAssociationEditor(
    ExdrfEditor["ParentTagAssociation"], Ui_QtParentTagAssociationEditor
):
    """A widget that allows the user to edit a ParentTagAssociation record."""

    def __init__(self, ctx: "QtContext", **kwargs):
        """Initialize the editor widget."""
        from exdrf_dev.db.models import (
            ParentTagAssociation as DbParentTagAssociation,
        )

        super().__init__(ctx=ctx, db_model=DbParentTagAssociation, **kwargs)
        self.setup_ui(self)

        self.verticalLayout.addChildWidget(self.create_button_box())

    def editing_changed(self, value: bool):
        pass

    def read_record(
        self, session: "Session", record_id: RecIdType
    ) -> "ParentTagAssociation":
        return session.scalar(
            self.selection.where(
                self.db_model.id == record_id  # type: ignore[operator]
            )
        )

    def populate(self, record: Union["ParentTagAssociation", None]):
        pass

    def save_to_record(
        self, record: "ParentTagAssociation", is_new: bool, session: "Session"
    ):
        pass

    def get_id_of_record(self, record: "ParentTagAssociation") -> RecIdType:
        return record.id
