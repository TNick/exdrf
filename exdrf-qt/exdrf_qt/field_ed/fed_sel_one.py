import logging
from typing import (
    TYPE_CHECKING,
    Any,
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
    from exdrf_qt.context import QtContext
    from exdrf_qt.controls.base_editor import ExdrfEditor
    from exdrf_qt.models import QtModel
    from exdrf_qt.models.record import QtRecord

logger = logging.getLogger(__name__)
DBM = TypeVar("DBM", bound="DrfSelOneEditor")


class DrfSelOneEditor(QWidget, Generic[DBM], DrfFieldEd):
    """Editor for selecting a related record.

    The control is a read-only line edit.
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
        **kwargs,
    ) -> None:

        logger.log(10, "DrfSelOneEditor.__init__")
        self._in_editing = True
        self._clear_action = None
        self._dropdown_action = None  # type: ignore
        self.line_edit = None  # type: ignore

        QWidget.__init__(self, kwargs.pop("parent", None))
        DrfFieldEd.__init__(self, ctx=ctx, **kwargs)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.create_line_edit()
        self.create_drop_down_action()
        self.create_clear_action()

        layout = QHBoxLayout(self)
        layout.addWidget(self.line_edit)
        layout.setContentsMargins(4, 0, 4, 0)

        self.popup = PopupWidget(parent=self, ctx=ctx, qt_model=qt_model)
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
        if not self._in_editing:
            logger.log(10, "DrfSelOneEditor.show_popup(): not in editing mode")
            return

        logger.log(10, "DrfSelOneEditor.show_popup()")
        self.popup.move(self.mapToGlobal(QPoint(0, self.height())))
        self.popup.resize(self.width(), 150)
        self.popup.show()
        self.popup.filter_edit.setFocus()

        self.popup.tree.blockSignals(True)
        index = QModelIndex()
        if self.field_value is None:
            logger.log(10, "Tree cleared")
        else:
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
        logger.log(10, "DrfSelOneEditor.on_item_selected(%s)", item.db_id)

        text = item.display_text()
        logger.log(10, "DrfSelOneEditor.on_item_selected: %s", text)

        self.line_edit.setText(text)
        self.popup.hide()

        self.field_value = item.db_id

    def resizeEvent(self, event: QResizeEvent | None) -> None:  # type: ignore
        logger.log(1, "DrfSelOneEditor.resizeEvent")
        super().resizeEvent(event)
        if self.popup and self.popup.isVisible():
            self.popup.resize(self.width(), 150)

    def create_line_edit(self) -> QLineEdit:
        """Creates a line edit for the field."""
        if self.line_edit is not None:
            return self.line_edit

        line_edit = QLineEdit(parent=self)
        line_edit.setReadOnly(True)
        line_edit.setPlaceholderText(self.t("cmn.NULL", "NULL"))
        line_edit.setClearButtonEnabled(False)
        self.line_edit = line_edit
        return line_edit

    def create_drop_down_action(self) -> QAction:
        """Creates a drop down action for the line edit."""
        if self._dropdown_action is not None:
            return self._dropdown_action

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
        if self._clear_action is not None:
            return self._clear_action

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
        self._in_editing = in_editing
        if not in_editing:
            if self.popup.isVisible():
                self.popup.hide()
        self._dropdown_action.setEnabled(in_editing)
        if self._clear_action:
            self._clear_action.setEnabled(
                in_editing and self.field_value is not None
            )

    def change_field_value(self, new_value: Any) -> None:
        """Change the field value.

        The new value can be a database record or an ID of a record.

        Args:
            new_value: The new value to set for the field.
        """
        if self._read_only:
            logger.log(10, "DrfSelOneEditor.change_field_value(): read only")
            return

        if new_value is None:
            logger.log(
                10,
                "DrfSelOneEditor.change_field_value(): None",
            )
            self.set_to_null()
            return

        # If we were provided with a database record, extract the ID.
        if hasattr(new_value, "metadata"):
            logger.log(
                10,
                "DrfSelOneEditor.change_field_value(): database record",
            )
            new_value = self.qt_model.get_db_item_id(new_value)

        logger.log(
            10,
            "DrfSelOneEditor.change_field_value() to %s (%s)",
            new_value,
            new_value.__class__.__name__,
        )
        import traceback

        logger.debug(traceback.format_stack())

        # If this is the same as the current value, do nothing.
        if new_value == self.field_value:
            logger.log(
                10,
                "DrfSelOneEditor.change_field_value(): same value: %s",
                new_value,
            )
            return

        # Attempt to locate the record in the model.
        loaded = False
        row = self.qt_model._db_to_row.get(new_value, None)
        if row is not None:
            record = self.qt_model.cache[row]
            if record.loaded:
                logger.log(
                    10,
                    "DrfSelOneEditor.change_field_value(): "
                    "record found in cache:",
                )
                self.line_edit.setText(self.record_to_text(record))
                loaded = True

        if not loaded:
            # If the record is not loaded, we need to load it ourselves.
            with self.qt_model.get_one_db_item_by_id(new_value) as db_item:
                if db_item is None:
                    logger.log(
                        10,
                        "DrfSelOneEditor.change_field_value(): "
                        "record not found: %s; setting to null",
                        new_value,
                    )
                    self.set_to_null()
                    return
                record = self.qt_model.db_item_to_record(db_item)
                logger.log(
                    10,
                    "DrfSelOneEditor.change_field_value(): "
                    "record loaded from database:",
                )
                self.line_edit.setText(self.record_to_text(record))

        self.qt_model.set_prioritized_ids([new_value])
        if self._clear_action:
            self._clear_action.setEnabled(True)
        self.field_value = new_value

    def set_to_null(self):
        """Set the field value to null."""
        if not self._in_editing:
            logger.log(
                10,
                "DrfSelOneEditor.set_to_null(): not in editing mode",
            )
            return

        self.field_value = None
        self.line_edit.setText("")
        if self._clear_action:
            self._clear_action.setEnabled(False)
        self.controlChanged.emit()

    def record_to_text(self, record: "QtRecord") -> str:
        """Convert a record to text."""
        data = record.get_row_data(role=Qt.ItemDataRole.DisplayRole)
        value = ", ".join([str(d) for d in data if d is not None])
        return value

    def load_value_from(self, record: Any):
        """Load the field value from the database record.

        Attributes:
            record: The item to load the field value from.
        """
        if not self._name:
            raise ValueError("Field name is not set.")
        related = getattr(record, self._name, None)
        if related is not None:
            related = self.qt_model.get_db_item_id(related)

        self.change_field_value(related)

    def save_value_to(self, record: Any):
        """Load the field value from the database record.

        Attributes:
            record: The item to load the field value from. May be the
                database record or the ID of the record.
        """
        if not self._name:
            raise ValueError("Field name is not set.")

        if self.field_value is None:
            setattr(record, self._name, None)
            return

        new_val = self.field_value
        if not hasattr(self.field_value, "metadata"):
            new_val = self.qt_model.get_db_items_by_id([new_val])[0]

        setattr(record, self._name, new_val)

    def change_nullable(self, value: bool) -> None:
        """Set the nullable property.

        The default implementation looks for an attribute called ac_clear
        in itself and, if found, assumes it is a QAction.
        """
        self._nullable = value
        if value:
            if self._clear_action is None:
                self._dropdown_action.deleteLater()
                self._dropdown_action = None  # type: ignore
                self.create_drop_down_action()
                self.create_clear_action()
        else:
            if self._clear_action is not None:
                self._clear_action.deleteLater()
                self._clear_action = None
