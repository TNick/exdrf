# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.
from typing import TYPE_CHECKING

from exdrf_qt.controls.table_list import ListDb

if TYPE_CHECKING:
    from exdrf_dev.db.models import Profile  # noqa: F401


class QtProfileList(ListDb["Profile"]):
    """Presents a list of records from the database."""

    def __init__(self, *args, **kwargs):
        from exdrf_dev.qt.profiles.models.profiles_full_model import (
            QtProfileFuMo,
        )
        from exdrf_dev.qt.profiles.widgets.profiles_editor import (
            QtProfileEditor,
        )

        super().__init__(editor=QtProfileEditor, *args, **kwargs)
        self.setModel(
            QtProfileFuMo(
                ctx=self.ctx,
                parent=self,
            )
        )
