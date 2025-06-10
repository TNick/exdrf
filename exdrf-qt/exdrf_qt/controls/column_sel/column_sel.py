from typing import TYPE_CHECKING, Generic

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QListWidgetItem

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.column_sel.column_sel_ui import Ui_ColumnSelDlg
from exdrf_qt.models.model import DBM, QtModel  # noqa: F401

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from exdrf_qt.controls.tree_header import ListDbHeader  # noqa: F401


class ColumnSelDlg(QDialog, Ui_ColumnSelDlg, QtUseContext, Generic[DBM]):
    """A dialog that allows the user to create a filter."""

    header: "ListDbHeader"

    def __init__(self, ctx: "QtContext", header: "ListDbHeader", **kwargs):
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
        h_model = header.model()
        assert h_model is not None

        self.c_visible.clear()
        self.c_available.clear()

        # Loop over *visual positions* (i.e., how columns are currently shown)
        for visual in range(header.count()):
            logical = header.logicalIndex(visual)
            column_name = h_model.headerData(logical, Qt.Orientation.Horizontal)
            item = QListWidgetItem(column_name)
            if header.isSectionHidden(logical):
                self.c_available.addItem(item)
            else:
                self.c_visible.addItem(item)
            item.setData(Qt.ItemDataRole.UserRole, logical)

    def apply_changes(self):
        # Read settings from the current layout.
        crt_settings = self.header.read_sections_layout()

        # Index them by the logical index.
        reshaped = {
            f_values["li"]: f_values for f_values in crt_settings.values()
        }

        # First go through the visible list and change the order.
        for i in range(self.c_visible.count()):
            logical_index = self.c_visible.item(i).data(
                Qt.ItemDataRole.UserRole
            )
            f_values = reshaped[logical_index]
            f_values["vi"] = i
            f_values["hidden"] = False

        offset = self.c_visible.count()

        # Next, go through the available list and change the order.
        for i in range(self.c_available.count()):
            logical_index = self.c_available.item(i).data(
                Qt.ItemDataRole.UserRole
            )
            f_values = reshaped[logical_index]
            f_values["vi"] = i + offset
            f_values["hidden"] = True

        # Apply the new order. We changed the dictionaries in place, so we
        # can use the same structure.
        self.header.apply_sections_layout(crt_settings, save_to_settings=True)

    # def apply_changes(self):
    #     header = self.header
    #     assert header is not None
    #     h_model = header.model()
    #     assert h_model is not None

    #     # Show all columns
    #     for i in range(header.count()):
    #         header.showSection(i)

    #     # Build the new order as a list of logical indexes, from visible list
    #     new_visible_logical = [
    #         self.c_visible.item(i).data(Qt.ItemDataRole.UserRole)
    #         for i in range(self.c_visible.count())
    #     ]

    #     # Move columns into the new positions one by one (always to the next
    #     # position)
    #     for target_visual, logical_index in enumerate(new_visible_logical):
    #         current_visual = header.visualIndex(logical_index)
    #         if current_visual != target_visual:
    #             header.moveSection(current_visual, target_visual)

    #     # Hide all columns in the hidden list.
    #     for i in range(self.c_available.count()):
    #         logical_index = self.c_available.item(i).data(
    #             Qt.ItemDataRole.UserRole
    #         )
    #         header.hideSection(logical_index)
