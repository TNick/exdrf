# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.
from typing import TYPE_CHECKING

from exdrf_qt.controls.table_list import ListDb

if TYPE_CHECKING:
    from exdrf_dev.db.models import Parent  # noqa: F401


class QtParentList(ListDb["Parent"]):
    """Presents a list of records from the database."""

    def __init__(self, *args, **kwargs):
        from exdrf_dev.qt.parents.models.parents_full_model import QtParentFuMo
        from exdrf_dev.qt.parents.widgets.parents_editor import QtParentEditor

        super().__init__(editor=QtParentEditor, *args, **kwargs)
        self.setModel(
            QtParentFuMo(
                ctx=self.ctx,
                parent=self,
            )
        )
