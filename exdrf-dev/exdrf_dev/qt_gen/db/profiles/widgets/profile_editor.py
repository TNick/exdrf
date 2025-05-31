# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> c/m/w/editor.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING, Union

from exdrf.constants import RecIdType
from exdrf_qt.controls import EditorDb

from exdrf_dev.qt_gen.db.profiles.widgets.profile_editor_ui import (
    Ui_QtProfileEditor,
)

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy.orm import Session  # noqa: F401

    from exdrf_dev.db.api import Profile  # noqa: F401


class QtProfileEditor(EditorDb["Profile"], Ui_QtProfileEditor):
    """A widget that allows the user to edit a Profile record."""

    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------

    def __init__(self, ctx: "QtContext", **kwargs):
        """Initialize the editor widget."""
        from exdrf_dev.db.api import Profile as DbProfile

        super().__init__(
            ctx=ctx,
            db_model=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.profiles.editor.model", DbProfile
            ),
            **kwargs,
        )
        self.verticalLayout.addWidget(self.create_button_box())
        # exdrf-keep-start extra_init -----------------------------------------

        # exdrf-keep-end extra_init -------------------------------------------

    def editing_changed(self, value: bool):
        pass

    def read_record(
        self, session: "Session", record_id: RecIdType
    ) -> "Profile":
        return session.scalar(
            self.selection.where(
                self.db_model.id == record_id,  # type: ignore
            )
        )

    def populate(self, record: Union["Profile", None]):
        self.c_id.setText(str(record.id) if record else "")
        self._populate(
            record,
            [
                "id",
            ],
        )

    def get_id_of_record(self, record: "Profile") -> RecIdType:
        return record.id

    # exdrf-keep-start extra_editor_content ------------------------------------

    # exdrf-keep-end extra_editor_content --------------------------------------


# exdrf-keep-start more_content ------------------------------------------------

# exdrf-keep-end more_content --------------------------------------------------
