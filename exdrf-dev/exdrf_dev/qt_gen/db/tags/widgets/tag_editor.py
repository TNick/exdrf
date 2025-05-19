# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/w/editor.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING, Union

from exdrf.constants import RecIdType
from exdrf_qt.controls import EditorDb

from exdrf_dev.qt_gen.db.tags.widgets.tag_editor_ui import Ui_QtTagEditor

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy.orm import Session  # noqa: F401

    from exdrf_dev.db.api import Tag  # noqa: F401


class QtTagEditor(EditorDb["Tag"], Ui_QtTagEditor):
    """A widget that allows the user to edit a Tag record."""

    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------

    def __init__(self, ctx: "QtContext", **kwargs):
        """Initialize the editor widget."""
        from exdrf_dev.db.api import Tag as DbTag

        super().__init__(ctx=ctx, db_model=DbTag, **kwargs)
        self.verticalLayout.addWidget(self.create_button_box())
        # exdrf-keep-start extra_init -----------------------------------------

        # exdrf-keep-end extra_init -------------------------------------------

    def editing_changed(self, value: bool):
        pass

    def read_record(self, session: "Session", record_id: RecIdType) -> "Tag":
        return session.scalar(
            self.selection.where(
                self.db_model.id == record_id,  # type: ignore[operator]
            )
        )

    def populate(self, record: Union["Tag", None]):
        self.c_id.setText(str(record.id) if record else "")
        self._populate(
            record,
            [
                "id",
            ],
        )

    def get_id_of_record(self, record: "Tag") -> RecIdType:
        return record.id

    # exdrf-keep-start extra_editor_content ------------------------------------

    # exdrf-keep-end extra_editor_content --------------------------------------


# exdrf-keep-start more_content ------------------------------------------------

# exdrf-keep-end more_content --------------------------------------------------
