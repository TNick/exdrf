# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/w/list.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING

from exdrf_qt.controls.table_list import ListDb

if TYPE_CHECKING:
    from exdrf_dev.db.api import Parent  # noqa: F401


class QtParentList(ListDb["Parent"]):
    """Presents a list of records from the database."""

    def __init__(self, *args, **kwargs):
        from exdrf_dev.qt_gen.db.parents.api import (
            QtParentEditor,
            QtParentFuMo,
        )

        super().__init__(editor=QtParentEditor, *args, **kwargs)
        self.setModel(
            QtParentFuMo(
                ctx=self.ctx,
                parent=self,
            )
        )
