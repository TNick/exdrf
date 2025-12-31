from typing import TYPE_CHECKING

from PyQt5.QtWidgets import QComboBox

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.seldb.db_config_delegate import DbConfigDelegate
from exdrf_qt.controls.seldb.db_config_model import DbConfigModel

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401


class ChooseDb(QComboBox, QtUseContext):
    """A combobox for choosing a database."""

    def __init__(self, ctx: "QtContext", **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx

        # Set up custom model and delegate
        model = DbConfigModel(ctx, self)
        self.setModel(model)
        delegate = DbConfigDelegate(ctx, self)
        self.setItemDelegate(delegate)

    def populate_db_connections(self):
        """Populate the combobox with database connections."""
        model = self.model()
        assert isinstance(model, DbConfigModel)
        model.populate_db_connections()

        return model
