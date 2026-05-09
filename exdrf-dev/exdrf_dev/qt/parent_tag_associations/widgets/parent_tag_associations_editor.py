# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.

from typing import TYPE_CHECKING, Union

from sqlalchemy import and_

from exdrf.constants import RecIdType
from exdrf_dev.qt.parent_tag_associations.widgets.parent_tag_associations_editor_ui import (
    Ui_QtParentTagAssociationEditor,
)
from exdrf_qt.controls.base_editor import ExdrfEditor

if TYPE_CHECKING:
    from sqlalchemy.orm import Session  # noqa: F401

    from exdrf_dev.db.models import ParentTagAssociation  # noqa: F401
    from exdrf_qt.context import QtContext  # noqa: F401


class QtParentTagAssociationEditor(
    ExdrfEditor["ParentTagAssociation"], Ui_QtParentTagAssociationEditor
):
    """A widget that allows the user to edit a ParentTagAssociation record."""

    def __init__(self, ctx: "QtContext", **kwargs):
        """Initialize the editor widget."""
        from exdrf_dev.db.models import (  # isort: skip
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
        if not isinstance(record_id, tuple) or len(record_id) != 2:
            raise TypeError(
                "ParentTagAssociation record_id must be a (parent_id, tag_id) tuple",
            )
        parent_id, tag_id = record_id[0], record_id[1]
        result = session.scalar(
            self.selection.where(
                and_(
                    self.db_model.parent_id == parent_id,
                    self.db_model.tag_id == tag_id,
                )
            )
        )
        if result is None:
            raise ValueError(
                "ParentTagAssociation not found for parent_id=%s tag_id=%s"
                % (parent_id, tag_id)
            )
        return result

    def populate(self, record: Union["ParentTagAssociation", None]):
        pass

    def save_to_record(
        self, record: "ParentTagAssociation", is_new: bool, session: "Session"
    ):
        pass

    def get_id_of_record(self, record: "ParentTagAssociation") -> RecIdType:
        return (record.parent_id, record.tag_id)
