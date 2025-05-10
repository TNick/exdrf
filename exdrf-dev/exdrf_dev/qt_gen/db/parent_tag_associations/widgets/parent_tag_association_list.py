# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/w/list.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING

from exdrf_qt.controls.table_list import ListDb

if TYPE_CHECKING:
    from exdrf_dev.db.api import ParentTagAssociation  # noqa: F401


class QtParentTagAssociationList(ListDb["ParentTagAssociation"]):
    """Presents a list of records from the database."""

    def __init__(self, *args, **kwargs):
        from exdrf_dev.qt_gen.db.parent_tag_associations.api import (
            QtParentTagAssociationEditor,
            QtParentTagAssociationFuMo,
        )

        super().__init__(editor=QtParentTagAssociationEditor, *args, **kwargs)
        self.setModel(
            QtParentTagAssociationFuMo(
                ctx=self.ctx,
                parent=self,
            )
        )
