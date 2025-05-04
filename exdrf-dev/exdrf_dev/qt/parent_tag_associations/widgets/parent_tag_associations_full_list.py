# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.
from typing import TYPE_CHECKING

from exdrf_qt.controls.table_list import ListDb

if TYPE_CHECKING:
    from exdrf_dev.db.models import ParentTagAssociation  # noqa: F401


class QtParentTagAssociationList(ListDb["ParentTagAssociation"]):
    """Presents a list of records from the database."""

    def __init__(self, *args, **kwargs):
        from exdrf_dev.qt.parent_tag_associations.models.parent_tag_associations_full_model import (
            QtParentTagAssociationFuMo,
        )
        from exdrf_dev.qt.parent_tag_associations.widgets.parent_tag_associations_editor import (
            QtParentTagAssociationEditor,
        )

        super().__init__(editor=QtParentTagAssociationEditor, *args, **kwargs)
        self.setModel(
            QtParentTagAssociationFuMo(
                ctx=self.ctx,
                parent=self,
            )
        )
