# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.
from typing import TYPE_CHECKING

from exdrf_qt.controls.table_list import ListDb

if TYPE_CHECKING:
    from exdrf_dev.db.models import Child  # noqa: F401


class QtChildList(ListDb["Child"]):
    """Presents a list of records from the database."""

    def __init__(self, *args, **kwargs):
        from exdrf_dev.qt.children.models.children_full_model import QtChildFuMo
        from exdrf_dev.qt.children.widgets.children_editor import QtChildEditor

        super().__init__(editor=QtChildEditor, *args, **kwargs)
        self.setModel(
            QtChildFuMo(
                ctx=self.ctx,
                parent=self,
            )
        )
