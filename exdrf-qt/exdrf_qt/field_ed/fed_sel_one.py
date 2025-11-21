import logging
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    Optional,
    Type,
    TypeVar,
)

from PyQt5.QtCore import (
    QModelIndex,
    QPoint,
    Qt,
)
from PyQt5.QtGui import QResizeEvent
from PyQt5.QtWidgets import (
    QAction,
    QHBoxLayout,
    QLineEdit,
    QWidget,
)

from exdrf_qt.controls.popup_list import PopupWidget
from exdrf_qt.field_ed.base import DrfFieldEd

if TYPE_CHECKING:
    from exdrf.constants import RecIdType

    from exdrf_qt.context import QtContext
    from exdrf_qt.controls.base_editor import ExdrfEditor
    from exdrf_qt.models import QtModel
    from exdrf_qt.models.record import QtRecord

logger = logging.getLogger(__name__)
DBM = TypeVar("DBM", bound="DrfSelOneEditor")


class DrfSelOneEditor(QWidget, Generic[DBM], DrfFieldEd):
    """Editor for selecting a single related record from a QtModel.

    This widget provides a user interface for selecting one related database
    record from a model. It consists of a read-only line edit that displays
    the currently selected record's display text, along with action buttons
    for opening a selection popup and clearing the selection.

    The selection mechanism uses a PopupWidget that displays a searchable tree
    view of records from the associated QtModel. When the user clicks the
    dropdown button, a popup appears below the line edit showing available
    records. The popup includes a search/filter field that allows filtering
    records in real-time. When a record is selected from the popup, it updates
    the line edit with the record's display text and stores the record's
    database ID as the field value.

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

    popup: "PopupWidget[DBM]"
    line_edit: QLineEdit
    _in_editing: bool
    _clear_action: Optional[QAction]
    _dropdown_action: QAction

    def __init__(
        self,
        ctx: "QtContext",
        qt_model: "QtModel[DBM]",
        editor_class: Optional[Type["ExdrfEditor"]] = None,
        add_kb: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> None:

        # Initialize logging and instance variables.
        logger.log(10, "DrfSelOneEditor.__init__")
        self._in_editing = True
        self._clear_action = None
        self._dropdown_action = None  # type: ignore
        self.line_edit = None  # type: ignore

        # Initialize parent classes.
        QWidget.__init__(self, kwargs.pop("parent", None))
        DrfFieldEd.__init__(self, ctx=ctx, **kwargs)

        # Configure widget focus behavior.
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Create UI components.
        self.create_line_edit()
        self.create_drop_down_action()
        self.create_clear_action()

        # Set up the layout with the line edit.
        layout = QHBoxLayout(self)
        layout.addWidget(self.line_edit)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create and connect the popup widget for record selection.
        self.popup = PopupWidget(
            parent=self,
            ctx=ctx,
            qt_model=qt_model,
            add_kb=add_kb,
        )
        self.popup.tree.itemSelected.connect(self.on_item_selected)

    @property
    def qt_model(self) -> "QtModel[DBM]":
        """Return the model."""
        return self.popup.qt_model  # type: ignore

    @qt_model.setter
    def qt_model(self, value: "QtModel[DBM]") -> None:
        """Set the model."""
        self.popup.qt_model = value

    def show_popup(self):
        """Show the popup."""
        # Prevent popup from opening if not in edit mode.
        if not self._in_editing:
            logger.log(
                10,
                "%s.show_popup(): not in editing mode",
                self.__class__.__name__,
            )
            return

        # Position and display the popup below the line edit.
        logger.log(10, "%s.show_popup()", self.__class__.__name__)
        self.popup.move(self.mapToGlobal(QPoint(0, self.height())))
        self.popup.resize(self.width(), 150)
        self.popup.show()
        self.popup.filter_edit.setFocus()

        # Set the current selection in the popup tree to match the field value.
        self.popup.tree.blockSignals(True)
        index = QModelIndex()
        if self.field_value is None:
            logger.log(10, "Tree cleared")
        else:
            # Find the row corresponding to the current field value.
            row = self.qt_model._db_to_row.get(self.field_value, None)
            logger.log(10, "Found row %s for value %s", row, self.field_value)
            if row is not None:
                index = self.qt_model.index(row, 0)
                logger.log(
                    10, "Found index %s for value %s", index, self.field_value
                )
            else:
                logger.log(
                    10,
                    "No row found for value %s",
                    self.field_value,
                )
        self.popup.tree.setCurrentIndex(index)
        self.popup.tree.blockSignals(False)

    def on_item_selected(self, item: "QtRecord"):
        # Handle selection of a record from the popup.
        logger.log(
            10, "%s.on_item_selected(%s)", self.__class__.__name__, item.db_id
        )

        # Update the line edit with the selected record's display text.
        text = item.display_text()
        logger.log(10, "%s.on_item_selected: %s", self.__class__.__name__, text)

        self.line_edit.setText(text)
        self.popup.hide()

        # Store the selected record's database ID as the field value.
        self.field_value = item.db_id

    def resizeEvent(self, event: QResizeEvent | None) -> None:  # type: ignore
        # Handle widget resize events.
        logger.log(1, "%s.resizeEvent", self.__class__.__name__)
        super().resizeEvent(event)
        # Resize the popup to match the widget width if it's visible.
        if self.popup and self.popup.isVisible():
            self.popup.resize(self.width(), 150)

    def create_line_edit(self) -> QLineEdit:
        """Creates a line edit for the field."""
        # Return existing line edit if already created.
        if self.line_edit is not None:
            return self.line_edit

        # Create and configure a read-only line edit widget.
        line_edit = QLineEdit(parent=self)
        line_edit.setReadOnly(True)
        line_edit.setPlaceholderText(self.t("cmn.NULL", "NULL"))
        line_edit.setClearButtonEnabled(False)
        self.line_edit = line_edit
        return line_edit

    def create_drop_down_action(self) -> QAction:
        """Creates a drop down action for the line edit."""
        # Return existing action if already created.
        if self._dropdown_action is not None:
            return self._dropdown_action

        # Create and configure the dropdown button action.
        action = QAction(self)
        action.setIcon(self.get_icon("bullet_arrow_down"))
        action.triggered.connect(self.show_popup)
        self.line_edit.addAction(
            action, QLineEdit.ActionPosition.TrailingPosition
        )
        self._dropdown_action = action
        return action

    def create_clear_action(self) -> QAction:
        """Creates a clear action for the line edit."""
        # Return existing action if already created.
        if self._clear_action is not None:
            return self._clear_action

        # Create and configure the clear button action.
        action = QAction(
            self.get_icon("clear_to_null_to_left"),
            self.t("cmn.clear_to_null", "Clear to NULL"),
            self,
        )
        action.triggered.connect(self.set_to_null)
        self.line_edit.addAction(
            action, QLineEdit.ActionPosition.TrailingPosition
        )
        self._clear_action = action
        return action

    def change_edit_mode(  # type: ignore
        self: QWidget, in_editing: bool  # type: ignore
    ) -> None:
        """Switch between edit mode and display mode.

        Default implementation sets the enabled state of the widget.

        Args:
            in_editing: True if the field is in edit mode, False if it
                is in display mode.
        """
        # Update the edit mode flag.
        self._in_editing = in_editing
        # Hide popup when switching to display mode.
        if not in_editing:
            if self.popup.isVisible():
                self.popup.hide()
        # Enable or disable the dropdown action based on edit mode.
        self._dropdown_action.setEnabled(in_editing)
        # Enable clear action only in edit mode and when a value is set.
        if self._clear_action:
            self._clear_action.setEnabled(
                in_editing and self.field_value is not None
            )

    def change_field_value(self, new_value: "None | DBM | RecIdType") -> None:
        """Change the field value.

        The new value can be a database record or an ID of a record.

        Args:
            new_value: The new value to set for the field.
        """
        # Prevent changes if the field is read-only.
        if self._read_only:
            logger.log(
                10,
                "%s.change_field_value(): read only",
                self.__class__.__name__,
            )
            return

        # Handle None values by clearing the field.
        if new_value is None:
            logger.log(
                10,
                "%s.change_field_value(): None",
                self.__class__.__name__,
            )
            self.set_to_null()
            return

        # Convert database record objects to their IDs.
        if hasattr(new_value, "metadata"):
            logger.log(
                10,
                "%s.change_field_value(): database record",
                self.__class__.__name__,
            )
            new_value = self.qt_model.get_db_item_id(new_value)  # type: ignore

        logger.log(
            1,
            "%s.change_field_value() to %s (%s)",
            self.__class__.__name__,
            new_value,
            new_value.__class__.__name__,
        )
        # import traceback
        # logger.debug(traceback.format_stack())

        # Skip update if the value hasn't changed.
        if new_value == self.field_value:
            logger.log(
                1,
                "%s.change_field_value(): same value: %s",
                self.__class__.__name__,
                new_value,
            )
            return

        # Try to find the record in the model cache first.
        loaded = False
        row = self.qt_model._db_to_row.get(new_value, None)
        if row is not None:
            record = self.qt_model.cache[row]
            if record.loaded:
                logger.log(
                    1,
                    "%s.change_field_value(): " "record found in cache:",
                    self.__class__.__name__,
                )
                self.line_edit.setText(self.record_to_text(record))
                loaded = True

        # Load the record from the database if not found in cache.
        if not loaded:
            with self.qt_model.get_one_db_item_by_id(new_value) as db_item:
                if db_item is None:
                    logger.log(
                        10,
                        "%s.change_field_value(): "
                        "record not found: %s; setting to null",
                        self.__class__.__name__,
                        new_value,
                    )
                    self.set_to_null()
                    return
                record = self.qt_model.db_item_to_record(db_item)
                logger.log(
                    10,
                    "%s.change_field_value(): " "record loaded from database:",
                    self.__class__.__name__,
                )
                self.line_edit.setText(self.record_to_text(record))

        # Update model priority and enable clear action, then set value.
        self.qt_model.set_prioritized_ids([new_value])
        if self._clear_action:
            self._clear_action.setEnabled(True)
        self.field_value = new_value

    def set_to_null(self):
        """Set the field value to null."""
        # Prevent clearing if not in edit mode.
        if not self._in_editing:
            logger.log(
                10,
                "%s.set_to_null(): not in editing mode",
                self.__class__.__name__,
            )
            return

        # Clear the field value and update the UI.
        self.field_value = None
        self.line_edit.setText("")
        if self._clear_action:
            self._clear_action.setEnabled(False)
        self.controlChanged.emit()

    def record_to_text(self, record: "QtRecord") -> str:
        """Convert a record to text."""
        # Get display data from the record and join non-None values.
        data = record.get_row_data(role=Qt.ItemDataRole.DisplayRole)
        value = ", ".join([str(d) for d in data if d is not None])
        return value

    def load_value_from(self, record: Any):
        """Load the field value from the database record.

        Attributes:
            record: The item to load the field value from.
        """
        # Validate that the field name is set.
        if not self._name:
            raise ValueError("Field name is not set.")
        # Get the related record from the database record.
        related = getattr(record, self._name, None)
        # Convert to ID if it's a database record object.
        if related is not None:
            related = self.qt_model.get_db_item_id(related)

        # Update the field value with the loaded related record ID.
        self.change_field_value(related)

    def save_value_to(self, record: Any):
        """Load the field value from the database record.

        Attributes:
            record: The item to load the field value from. May be the
                database record or the ID of the record.
        """
        # Validate that the field name is set.
        if not self._name:
            raise ValueError("Field name is not set.")

        # Handle None values by setting the attribute to None.
        if self.field_value is None:
            setattr(record, self._name, None)
            return

        # Convert ID to database record object if necessary.
        new_val = self.field_value
        if not hasattr(self.field_value, "metadata"):
            new_val = self.qt_model.get_db_items_by_id([new_val])[0]

        # Save the value to the record.
        setattr(record, self._name, new_val)

    def change_nullable(self, value: bool) -> None:
        """Set the nullable property.

        The default implementation looks for an attribute called ac_clear
        in itself and, if found, assumes it is a QAction.
        """
        # Update the nullable flag.
        self._nullable = value
        # Add clear action if field becomes nullable.
        if value:
            if self._clear_action is None:
                # Recreate dropdown action to allow clear action placement.
                self._dropdown_action.deleteLater()
                self._dropdown_action = None  # type: ignore
                self.create_drop_down_action()
                self.create_clear_action()
        # Remove clear action if field becomes non-nullable.
        else:
            if self._clear_action is not None:
                self._clear_action.deleteLater()
                self._clear_action = None

    def setEnabled(self, enabled: bool) -> None:  # type: ignore
        """Set the enabled state of the widget."""
        super().setEnabled(enabled)
        self.line_edit.setEnabled(enabled)
        if self._dropdown_action:
            self._dropdown_action.setEnabled(enabled)
        if self._clear_action:
            self._clear_action.setEnabled(enabled)
