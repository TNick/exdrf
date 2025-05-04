# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.
from typing import TYPE_CHECKING

from exdrf_qt.controls.table_list import ListDb

if TYPE_CHECKING:
    from exdrf_dev.db.models import CompositeKeyModel  # noqa: F401


class QtCompositeKeyModelList(ListDb["CompositeKeyModel"]):
    """Presents a list of records from the database."""

    def __init__(self, *args, **kwargs):
        from exdrf_dev.qt.composite_key_models.models.composite_key_models_full_model import (
            QtCompositeKeyModelFuMo,
        )
        from exdrf_dev.qt.composite_key_models.widgets.composite_key_models_editor import (
            QtCompositeKeyModelEditor,
        )

        super().__init__(editor=QtCompositeKeyModelEditor, *args, **kwargs)
        self.setModel(
            QtCompositeKeyModelFuMo(
                ctx=self.ctx,
                parent=self,
            )
        )
