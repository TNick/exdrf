# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.
from typing import TYPE_CHECKING

from exdrf_qt.controls.table_list import ListDb

if TYPE_CHECKING:
    from exdrf_dev.db.models import Tag  # noqa: F401


class QtTagList(ListDb["Tag"]):
    """Presents a list of records from the database."""

    def __init__(self, *args, **kwargs):
        from exdrf_dev.qt.tags.models.tags_full_model import QtTagFuMo
        from exdrf_dev.qt.tags.widgets.tags_editor import QtTagEditor

        super().__init__(editor=QtTagEditor, *args, **kwargs)
        self.setModel(
            QtTagFuMo(
                ctx=self.ctx,
                parent=self,
            )
        )
