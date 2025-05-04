# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.
from typing import TYPE_CHECKING

from exdrf_qt.controls.table_list import ListDb

if TYPE_CHECKING:
    from exdrf_dev.db.models import RelatedItem  # noqa: F401


class QtRelatedItemList(ListDb["RelatedItem"]):
    """Presents a list of records from the database."""

    def __init__(self, *args, **kwargs):
        from exdrf_dev.qt.related_items.models.related_items_full_model import (
            QtRelatedItemFuMo,
        )
        from exdrf_dev.qt.related_items.widgets.related_items_editor import (
            QtRelatedItemEditor,
        )

        super().__init__(editor=QtRelatedItemEditor, *args, **kwargs)
        self.setModel(
            QtRelatedItemFuMo(
                ctx=self.ctx,
                parent=self,
            )
        )
