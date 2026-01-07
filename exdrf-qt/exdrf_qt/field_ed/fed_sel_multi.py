import logging
from typing import (
    TYPE_CHECKING,
    Any,
    List,
    TypeVar,
    cast,
)

from PyQt5.QtCore import QItemSelection, QItemSelectionModel
from PyQt5.QtWidgets import QAbstractItemView
from sqlalchemy import inspect

from exdrf_qt.field_ed.fed_sel_one import DrfSelBase

if TYPE_CHECKING:
    from exdrf.constants import RecIdType
    from exdrf.field import ExField

    from exdrf_qt.controls.tree_list import TreeView
    from exdrf_qt.models.record import QtRecord

logger = logging.getLogger(__name__)
DBM_M = TypeVar("DBM_M", bound="DrfSelMultiEditor")
ITEMS_IN_LABEL = 2


class DrfSelMultiEditor(DrfSelBase[DBM_M]):
    """Editor for selecting multiple related records from a QtModel.

    This widget provides a user interface for selecting multiple related
    database records from a model. It consists of a read-only line edit that
    displays the currently selected records' display text, along with action
    buttons for opening a selection popup and clearing the selection.

    The selection mechanism uses a PopupWidget that displays a searchable tree
    view of records from the associated QtModel. When the user clicks the
    dropdown button, a popup appears below the line edit showing available
    records. The popup includes a search/filter field that allows filtering
    records in real-time. When a record is selected from the popup, it updates
    the line edit with the record's text (if they are a few)
    or the number of selected records (if there are many).

    The widget supports both edit and display modes. In edit mode, the dropdown
    and clear buttons are enabled, allowing users to change the selection. In
    display mode, these buttons are disabled, making the field read-only.

    If the field is nullable, a clear button is displayed that allows setting
    the value to null. The clear button is automatically enabled or disabled
    based on whether a value is currently selected and whether the field is in
    edit mode.

    The widget integrates with the field editing system through the DrfFieldEd
    base class, providing methods to load values from database records and
    save values back to them. It can handle both database record objects and
    record IDs as values, automatically converting between them as needed.

    Attributes:
        popup: The popup widget containing the searchable tree view for
            record selection.
        line_edit: The read-only line edit displaying the selected record's
            text.
        _in_editing: Flag indicating whether the widget is in edit mode.
        _clear_action: Optional action button for clearing the selection,
            present only when the field is nullable.
        _dropdown_action: Action button for opening the selection popup.
    """

    def post_popup_init(self):
        tree = cast("TreeView", self.popup.tree)
        tree.itemsSelected.connect(self.on_items_selected)
        tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

    def on_show_popup(self):

        tree = cast("TreeView", self.popup.tree)
        sm = tree.selectionModel()
        if sm is None:
            return

        sm.clearSelection()
        if self.field_value is None:
            logger.log(1, "Tree cleared")
            return

        # Collect all indices to select in a single batch operation.
        selection = QItemSelection()
        for crt_id in self.field_value:
            # Find the row corresponding to the current field value.
            row = self.qt_model._db_to_row.get(crt_id, None)
            logger.log(1, "Found row %s for value %s", row, crt_id)
            if row is not None:
                index = self.qt_model.index(row, 0)
                logger.log(1, "Found index %s for value %s", index, crt_id)
                # Add the index to the selection range.
                selection.select(index, index)
            else:
                logger.log(
                    1,
                    "No row found for value %s",
                    crt_id,
                )

        # Apply all selections in a single operation.
        if not selection.isEmpty():
            sm.select(
                selection,
                cast(
                    "QItemSelectionModel.SelectionFlag",
                    sm.SelectionFlag.Select | sm.SelectionFlag.Rows,
                ),
            )

    def on_items_selected(self, items: List["QtRecord"]):
        # Handle selection of a record from the popup.
        logger.log(
            1, "%s.on_item_selected(%s)", self.__class__.__name__, len(items)
        )
        self._sel_field_value([i.db_id for i in items], False)

    def _sel_field_value(
        self,
        new_value: "List[DBM_M | RecIdType]",
        change_priority_ids: bool = True,
    ) -> bool:
        """Change the field value.

        The new value can be a database record or an ID of a record.

        Args:
            new_value: The new value to set for the field.
        """
        converted = []
        for itr in new_value:
            if hasattr(itr, "metadata"):
                logger.log(
                    1,
                    "%s.change_field_value(): database record",
                    self.__class__.__name__,
                )
                itr = self.qt_model.get_db_item_id(itr)  # type: ignore
            if itr is not None:
                converted.append(itr)

        crt_val = self.field_value
        if crt_val is None:
            crt_val = []
        else:
            crt_val = list(crt_val)
        if crt_val == converted:
            return False

        if len(converted) > ITEMS_IN_LABEL:
            label = self.t(
                "cmn.sel_count",
                "{cnt} selected",
                cnt=len(converted),
            )
        else:
            with self.ctx.same_session():
                label = ", ".join(
                    [self.get_record_label(itr) for itr in converted]
                )
        self.line_edit.setText(f"[{label}]" if label else "")

        # Update model priority and enable clear action, then set value.
        if change_priority_ids:
            self.qt_model.set_prioritized_ids(converted)
        else:
            self.qt_model.prioritized_ids = converted
        self.field_value = converted
        return True

    def save_value_to(self, record: Any):
        # Validate that the field name is set.
        if not self._name:
            raise ValueError("Field name is not set.")

        # Convert ID to database record object if necessary.
        new_vals = []
        if self.field_value is not None:
            for itr in self.field_value:
                if not hasattr(itr, "metadata"):
                    new_vals.append(self.qt_model.get_db_items_by_id([itr])[0])
                else:
                    new_vals.append(itr)

        # Save the value to the record.
        mapper = inspect(record.__class__)
        relationship = mapper.relationships[self._name]
        setattr(record, self._name, relationship.collection_class(new_vals))

    def create_ex_field(self) -> "ExField":
        from exdrf.field_types.ref_m2m import RefManyToManyField

        # TODO: ref and ref_intermediate should be set to models.
        return RefManyToManyField(
            name=self.name,
            description=self.description or "",
            nullable=self.nullable,
            ref=self.qt_model.db_model,  # type: ignore
            ref_intermediate=self.qt_model.db_model,  # type: ignore
        )

    def on_record_saved(self, record: DBM_M) -> None:
        """The record has been saved."""
        rec_id = self.qt_model.get_db_item_id(record)
        crt_list = self.field_value
        if crt_list is None:
            crt_list = [rec_id]
        else:
            crt_list = list(crt_list)
            if rec_id in crt_list:
                return
            crt_list.append(rec_id)
        self.change_field_value(crt_list)

    def set_to_null(self):
        """Set the field value to null."""
        # Prevent clearing if not in edit mode.
        if not self._in_editing:
            logger.log(
                1,
                "%s.set_to_null(): not in editing mode",
                self.__class__.__name__,
            )
            return

        # Clear the field value and update the UI.
        self.field_value = []
        self.line_edit.setText("")
        if self._clear_action:
            self._clear_action.setEnabled(False)
        self.controlChanged.emit()
