from typing import TYPE_CHECKING, Generic

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QDialogButtonBox

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.column_sel.column_sel_ui import Ui_ColumnSelDlg
from exdrf_qt.models.model import DBM, QtModel  # noqa: F401

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QHeaderView  # noqa: F401

    from exdrf_qt.context import QtContext  # noqa: F401


class ColumnSelDlg(QDialog, Ui_ColumnSelDlg, QtUseContext, Generic[DBM]):
    """A dialog that allows the user to create a filter."""

    def __init__(self, ctx: "QtContext", header: "QHeaderView", **kwargs):
        """Initialize the editor widget."""
        super().__init__(**kwargs)
        self.ctx = ctx
        self.header = header
        self.setup_ui(self)

        # Populate lists
        self.populate_lists()

        # Connect the apply button.
        btn_apply = self.bbox.button(QDialogButtonBox.StandardButton.Apply)
        assert btn_apply is not None
        btn_apply.clicked.connect(self.accept)

    def populate_lists(self):
        header = self.header
        assert header is not None
        h_model = header.model()
        assert h_model is not None

        self.c_visible.clear()
        self.c_available.clear()

        # Loop over *visual positions* (i.e., how columns are currently shown)
        for visual in range(header.count()):
            logical = header.logicalIndex(visual)
            column_name = h_model.headerData(logical, Qt.Orientation.Horizontal)
            if header.isSectionHidden(logical):
                self.c_available.addItem(column_name)
            else:
                self.c_visible.addItem(column_name)

    def apply_changes(self):
        header = self.header
        assert header is not None
        h_model = header.model()
        assert h_model is not None

        # 1. Hide all columns
        for i in range(header.count()):
            header.hideSection(i)

        # 2. Build a map from column name to logical index
        name_to_logical = {
            h_model.headerData(j, Qt.Orientation.Horizontal): j
            for j in range(header.count())
        }

        # 3. Build the new order as a list of logical indexes, from visible list
        new_visible_logical = [
            name_to_logical[self.c_visible.item(i).text()]
            for i in range(self.c_visible.count())
        ]

        # 4. Move columns into the new positions one by one (always to the next position)
        for target_visual, logical_index in enumerate(new_visible_logical):
            current_visual = header.visualIndex(logical_index)
            if current_visual != target_visual:
                header.moveSection(current_visual, target_visual)
            header.showSection(logical_index)
