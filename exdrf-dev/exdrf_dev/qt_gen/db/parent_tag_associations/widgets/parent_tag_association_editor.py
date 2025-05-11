# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/w/editor.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING, Any, Union, cast

from exdrf.constants import RecIdType
from exdrf_qt.controls import EditorDb

from exdrf_dev.qt_gen.db.parent_tag_associations.widgets.parent_tag_association_editor_ui import (
    Ui_QtParentTagAssociationEditor,
)

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy.orm import Session  # noqa: F401

    from exdrf_dev.db.api import ParentTagAssociation  # noqa: F401


class QtParentTagAssociationEditor(
    EditorDb["ParentTagAssociation"], Ui_QtParentTagAssociationEditor
):
    """A widget that allows the user to edit a ParentTagAssociation record."""

    def __init__(self, ctx: "QtContext", **kwargs):
        """Initialize the editor widget."""
        from exdrf_dev.db.api import (
            ParentTagAssociation as DbParentTagAssociation,
        )

        super().__init__(ctx=ctx, db_model=DbParentTagAssociation, **kwargs)
        self.verticalLayout.addWidget(self.create_button_box())

    def editing_changed(self, value: bool):
        pass

    def read_record(
        self, session: "Session", record_id: RecIdType
    ) -> "ParentTagAssociation":
        return session.scalar(
            self.selection.where(
                self.db_model.parent_id == record_id[0],  # type: ignore[operator]
                self.db_model.tag_id == record_id[1],  # type: ignore[operator]
            )
        )

    def populate(self, record: Union["ParentTagAssociation", None]):
        self.c_parent_id.setText(str(record.parent_id) if record else "")
        self.c_tag_id.setText(str(record.tag_id) if record else "")
        self._populate(
            record,
            [
                "parent_id",
                "tag_id",
            ],
        )

    def get_id_of_record(self, record: "ParentTagAssociation") -> RecIdType:
        return cast(
            Any,
            (
                record.parent_id,
                record.tag_id,
            ),
        )
