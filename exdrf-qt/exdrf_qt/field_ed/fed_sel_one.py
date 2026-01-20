import logging
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    cast,
)

from PyQt5.QtCore import (
    QModelIndex,
    QPoint,
    Qt,
    pyqtSignal,
)
from PyQt5.QtGui import QMouseEvent, QResizeEvent
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
    QHBoxLayout,
    QLineEdit,
    QWidget,
)
from sqlalchemy import func, select

from exdrf_qt.controls.popup_list import PopupWidget
from exdrf_qt.field_ed.base import DrfFieldEd
from exdrf_qt.utils.tlh import top_level_handler

if TYPE_CHECKING:
    from exdrf.constants import RecIdType
    from exdrf.field import ExField

    from exdrf_qt.context import QtContext
    from exdrf_qt.controls.base_editor import ExdrfEditor
    from exdrf_qt.controls.tree_list import TreeView
    from exdrf_qt.models import QtModel
    from exdrf_qt.models.record import QtRecord

logger = logging.getLogger(__name__)
DBM = TypeVar("DBM")
DBM_O = TypeVar("DBM_O")


class ClickableLineEdit(QLineEdit):
    """A QLineEdit that emits a clicked signal when clicked.

    It is used as the resting-phase control (the one normally shown, when the
    user is not interacting with the widget) for DrfSelBase.

    We subclass it so that we can show the popup when the user clicks on it.
    """

    clicked = pyqtSignal()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore
        """Handle mouse press events and emit clicked signal."""
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


class DrfSelBase(QWidget, Generic[DBM], DrfFieldEd):
    """Common base class for single-selection and multi-selection widgets.

    Attributes:
        popup: The popup widget. When the widget is constructed, the popup is
            not created. It is created when the user clicks on the line edit.
            When the popup is created, it is set to the model passed to the
            constructor.
        line_edit: The control shown when the user is not interacting with
            the widget.
        _in_editing: Whether the widget is in editing mode.
        _clear_action: The clear action that we show inside the line edit.
        _dropdown_action: The dropdown action that we show inside the line edit.
        _edit_action: The edit action that we show inside the line edit.
        _editor_class: The editor class.
        _qt_model: The model.
        _add_kb: The add keyboard action.
    """

    popup: "PopupWidget[DBM]"
    line_edit: "ClickableLineEdit"
    _in_editing: bool
    _clear_action: Optional[QAction]
    _dropdown_action: QAction
    _edit_action: Optional[QAction]
    _editor_class: Optional[Type["ExdrfEditor"]]
    _qt_model: "QtModel[DBM]"
    _add_kb: Optional[Callable[[str], None]]

    def __init__(
        self,
        ctx: "QtContext",
        qt_model: "QtModel[DBM]",
        editor_class: Optional[Type["ExdrfEditor"]] = None,
        add_kb: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> None:

        # Initialize instance variables.
        logger.log(1, "DrfSelOneEditor.__init__")
        self._in_editing = True
        self._qt_model = qt_model
        self._clear_action = None
        self._dropdown_action = None  # type: ignore
        self._edit_action = None
        self.line_edit = None  # type: ignore
        self._editor_class = editor_class

        # Initialize parent classes.
        QWidget.__init__(self, kwargs.pop("parent", None))
        DrfFieldEd.__init__(self, ctx=ctx, **kwargs)

        # Configure widget focus behavior.
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Create UI components.
        self.create_line_edit()
        self.create_drop_down_action()
        self.create_edit_action()
        self.create_clear_action()
        self.change_nullable(self._nullable)

        # Set up the layout with the line edit.
        layout = QHBoxLayout(self)
        layout.addWidget(self.line_edit)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create and connect the popup widget for record selection.
        if not add_kb and self._editor_class is not None:
            add_kb = self.auto_create_new
        self._add_kb = add_kb
        self.popup = None

        self.controlChanged.connect(self.on_value_changed)
        self.post_init()

    @property
    def qt_model(self) -> "QtModel[DBM]":
        """Return the model."""
        return self._qt_model  # type: ignore

    @qt_model.setter
    def qt_model(self, value: "QtModel[DBM]") -> None:
        """Set the model."""
        self._qt_model = value
        if self.popup is not None:
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
        if self.popup is None:
            if self._qt_model.partially_initialized:
                # This happens when the model is constructed with the
                # prevent_total_count flag set to True.
                self._qt_model.recalculate_total_count()
            self.popup = PopupWidget(
                parent=self,
                ctx=self.ctx,
                qt_model=self._qt_model,
                add_kb=self._add_kb,
            )
            self.post_popup_init()

        # Position and display the popup below the line edit.
        logger.log(1, "%s.show_popup()", self.__class__.__name__)
        self.popup.move(self.mapToGlobal(QPoint(0, self.height())))
        self.popup.resize(self.width(), 150)
        self.popup.show()
        self.popup.filter_edit.setFocus()

        # Allow subclasses to do additional setup.
        with self.popup.block_signals():
            self.on_show_popup()

    def post_init(self):
        """Perform additional initialization after the widget is created."""

    def post_popup_init(self):
        """Perform additional initialization after the popup is constructed."""

    def on_item_selected(self, item: "QtRecord"):
        """The item has been selected from the popup."""

    def on_show_popup(self):
        """The popup is about to be shown.

        Allows subclasses to do additional setup."""

    def resizeEvent(self, event: QResizeEvent | None) -> None:  # type: ignore
        # Handle widget resize events.
        logger.log(1, "%s.resizeEvent", self.__class__.__name__)
        super().resizeEvent(event)
        # Resize the popup to match the widget width if it's visible.
        if self.popup and self.popup.isVisible():
            self.popup.resize(self.width(), 150)

    def create_line_edit(self) -> ClickableLineEdit:
        """Creates a line edit for the field."""
        # Return existing line edit if already created.
        if self.line_edit is not None:
            return self.line_edit

        # Create and configure a read-only line edit widget.
        line_edit = ClickableLineEdit(parent=self)
        line_edit.setReadOnly(True)
        line_edit.setPlaceholderText(self.t("cmn.NULL", "NULL"))
        line_edit.setClearButtonEnabled(False)
        line_edit.clicked.connect(self.show_popup)
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

    def create_edit_action(self) -> Optional[QAction]:
        """Creates an action that allows the user to edit the current selection.

        If the editor class is not set, no action is created.
        """
        # Return existing action if already created.
        if self._edit_action is not None:
            return self._edit_action
        if self._editor_class is None:
            return None

        # Create and configure the action.
        action = QAction(self)
        action.setIcon(self.get_icon("edit_button"))
        action.triggered.connect(self.on_edit_item)
        self.line_edit.addAction(
            action, QLineEdit.ActionPosition.TrailingPosition
        )
        self._edit_action = action
        return action

    def create_clear_action(self) -> QAction:
        """Creates a clear action for the line edit."""
        # Return existing action if already created.
        if self._clear_action is not None:
            return self._clear_action

        # Create and configure the clear button action.
        action = QAction(
            self.get_icon("clear_to_null"),
            self.t("cmn.clear_to_null", "Clear to NULL"),
            self,
        )
        action.triggered.connect(self.set_to_null)
        self.line_edit.addAction(
            action, QLineEdit.ActionPosition.LeadingPosition
        )
        self._clear_action = action
        return action

    def setEnabled(self, enabled: bool) -> None:  # type: ignore
        """Set the enabled state of the widget."""
        super().setEnabled(enabled)
        self.line_edit.setEnabled(enabled)
        if self._dropdown_action:
            self._dropdown_action.setEnabled(enabled)
        if self._clear_action:
            self._clear_action.setEnabled(enabled)
        if self._edit_action:
            self._edit_action.setEnabled(enabled)

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

    def change_nullable(self, value: bool) -> None:
        """Set the nullable property.

        The default implementation looks for an attribute called ac_clear
        in itself and, if found, assumes it is a QAction.
        """
        # Update the nullable flag.
        self._nullable = value
        # Defer until actions are created.
        if self._dropdown_action is None:
            return

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
        self.field_value = None
        self.line_edit.setText("")
        if self._clear_action:
            self._clear_action.setEnabled(False)
        if self._edit_action:
            self._edit_action.setEnabled(False)
        self.controlChanged.emit()

    def record_to_text(self, record: "QtRecord") -> str:
        """Convert a record to text."""
        # Get display data from the record and join non-None values.
        data = record.get_row_data(role=Qt.ItemDataRole.DisplayRole)
        value = ", ".join([str(d) for d in data if d is not None])
        return value

    def change_field_value(self, new_value: Any) -> None:
        """Change the field value.

        The new value can be a database record or an ID of a record.

        Args:
            new_value: The new value to set for the field.
        """
        # Prevent changes if the field is read-only.
        if self._read_only:
            logger.log(
                1,
                "%s.change_field_value(): read only",
                self.__class__.__name__,
            )
            return

        # Handle None values by clearing the field.
        if new_value is None:
            logger.log(
                1,
                "%s.change_field_value(): None",
                self.__class__.__name__,
            )
            self.set_to_null()
            return

        self._sel_field_value(new_value)

    @top_level_handler
    def on_value_changed(self):
        # React to the new value.
        enabled = not self.is_empty
        if self._clear_action:
            self._clear_action.setEnabled(enabled)
        if self._edit_action:
            self._edit_action.setEnabled(enabled)

    def _sel_field_value(self, new_value: Any) -> bool:
        """Change the field value.

        The new value can be a database record or an ID of a record.

        Args:
            new_value: The new value to set for the field.

        Returns:
            True if the field value has been changed to the proposed value.
        """
        raise NotImplementedError("Subclasses must implement this method")

    def get_record_label(self, record_id: "RecIdType") -> str:
        # Try to find the record in the model cache first.
        assert record_id is not None
        row = self.qt_model._db_to_row.get(record_id, None)
        if row is not None:
            record = self.qt_model.cache[row]
            if record.loaded:
                logger.log(
                    1,
                    "%s.change_field_value(): " "record found in cache:",
                    self.__class__.__name__,
                )
                return self.record_to_text(record)

        # Load the record from the database if not found in cache.
        with self.qt_model.get_one_db_item_by_id(record_id) as db_item:
            if db_item is None:
                logger.log(
                    1,
                    "%s.change_field_value(): "
                    "record not found: %s; setting to null",
                    self.__class__.__name__,
                    record_id,
                )
                self.set_to_null()
                return ""
            record = self.qt_model.db_item_to_record(db_item)
            logger.log(
                1,
                "%s.change_field_value(): " "record loaded from database:",
                self.__class__.__name__,
            )
            return self.record_to_text(record)

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

        # Update the field value with the loaded related record ID.
        self.change_field_value(related)

    @top_level_handler
    def auto_create_new(self, text: str) -> None:
        """Create a new record."""

        # Create the editor widget.
        editor = self.create_editor()
        if editor is None:
            return

        # Prepare it for creating a new record.
        editor.on_create_new()

    def on_record_saved(self, record: DBM) -> None:
        """The record has been saved in the external editor."""
        raise NotImplementedError("Subclasses must implement this method")

    def create_editor(self, **kwargs) -> Optional["ExdrfEditor"]:
        """Create the editor widget."""
        # No need for the popup anymore.
        if self.popup.isVisible():
            self.popup.hide()

        if self.qt_model is None:
            logger.error("No model set")
            return None

        # This should only be called when there's an editor class set.
        if self._editor_class is None:
            logger.error("No editor class set")
            return None

        # Create the editor widget and prepare it for creating a new record.
        editor = self._editor_class(
            ctx=self.ctx,
            db_model=self.qt_model.db_model,
            parent=self,
            parent_form=self.form,
            **kwargs,
        )

        # React to the record being saved.
        def _on_record_saved(record: DBM) -> None:
            """The record has been saved."""
            self.on_record_saved(record)
            self.ctx.close_window(editor)

        editor.recordSaved.connect(_on_record_saved)

        # Create the panel for it.
        self.ctx.create_window(editor, title=editor.windowTitle())

        return editor

    @top_level_handler
    def on_edit_item(self):
        """Opens the edit dialog for the current item."""

        raise NotImplementedError

    def constraints_changed(self, concept_key: str, new_value: Any) -> None:
        """React to the constraints being changed.

        Args:
            concept_key: The key of the concept that has changed.
            new_value: The new value of the concept.
        """
        from exdrf.filter import validate_filter

        from exdrf_qt.models.selector import Selector

        try:
            if self._qt_model is None:
                logger.error("No model set")
                return

            self._qt_model.constraints_changed(concept_key, new_value)
            if self.is_empty:
                logger.log(1, "No field value set, nothing to check")
                return

            # If the model is initialized, the constraints_changed would
            # have triggered a model reset which, in turn, would trigger
            # an items count computation. If that value is 0, there's no
            # point doing the check below as the field will be set to null.
            if not self._qt_model.partially_initialized:
                if self._qt_model.total_count == 0:
                    logger.log(
                        1,
                        "Model is initialized and total count is 0, "
                        "nothing to check",
                    )
                    self.set_to_null()
                    return

            # Compute the filter for this constraint.
            flt = self._qt_model.get_constraint_filter(concept_key, new_value)
            if not flt:
                logger.debug("No filter found for concept %s", concept_key)
                self.set_to_null()
                return

            # Make sure that the filter is valid.
            validate_result = validate_filter(flt)
            if validate_result:
                logger.error(
                    "Invalid filter for concept %s: %s",
                    concept_key,
                    validate_result,
                )
                self.set_to_null()
                return

            # Create a selector that uses this filter...
            selector = Selector[DBM].from_qt_model(
                self._qt_model,
                dialect=(
                    self.ctx.engine.dialect.name
                    if self.ctx.engine is not None
                    else None
                ),
            )
            stm = selector.run(flt)
            if stm is None:
                logger.error("No selection found for concept %s", concept_key)
                self.set_to_null()
                return

            # ...and see if the current ID is in the selection.
            stm = stm.where(
                self._qt_model.get_id_filter([self._field_value]),
            )
            with self.ctx.same_session() as session:
                count_stmt = select(func.count()).select_from(stm.subquery())
                result = session.scalar(count_stmt)

                # If the current ID is not in the selection, set the field to
                # null.
                if not result:
                    logger.error(
                        "Current ID %s not found in selection for concept %s",
                        self._field_value,
                        concept_key,
                    )
                    self.set_to_null()
                else:
                    logger.debug(
                        "Count for concept %s is %d", concept_key, result
                    )
        except Exception as e:
            logger.error(
                "Error in constraints_changed for concept %s: %s",
                concept_key,
                e,
                exc_info=True,
            )

    def get_provides(self, default: Optional[List[str]] = None) -> List[str]:
        """Get the provides for the field.

        Usually the resource will indicate the providers and that
        list is available in default. That provider may be overridden at the
        field level using the provides property.

        Args:
            default: The default provides for the field.

        Returns:
            The provides for the field.
        """
        prop_prov = self.property("provides")
        if prop_prov is not None:
            result = [p.strip() for p in prop_prov.split(",") if p.strip()]
            if result:
                return result
        return default or []

    def get_depends_on(self, default: Optional[List[str]] = None) -> List[str]:
        """Get the depends on for the field."""
        prop_deps = self.property("depends_on")
        if prop_deps is not None:
            result = []
            for part in prop_deps.split(","):
                if not part.strip():
                    continue
                concept, target = part.strip().split(":", maxsplit=1)
                result.append((concept.strip(), target.strip()))
            if result:
                return result
        return default or []

    def integrate_concepts(self, provides: List[str], depends_on: List[str]):
        """Helper for set_form that allows you to declare in one go
        both the concept we provide and the ones that we depend on.
        """
        if not self.form:
            logger.error("Form is not set for %s", self.__class__.__name__)
            return

        for concept in self.get_provides(provides):
            self.form.constraints.register_provider(
                concept=concept,
                provider=self,
            )

        for concept in self.get_depends_on(depends_on):
            self.form.constraints.register_subscriber(
                concept=concept,
                subscriber=self,
            )


class DrfSelOneEditor(DrfSelBase[DBM_O]):
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
        _edit_action: Optional action button for editing the current selection.
    """

    def post_popup_init(self):
        tree = cast("TreeView", self.popup.tree)
        tree.itemSelected.connect(self.on_item_selected)
        tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

    def on_show_popup(self):
        # Set the current selection in the popup tree to match the field value.
        index = QModelIndex()
        if self.field_value is None:
            logger.log(1, "Tree cleared")
        else:
            # Find the row corresponding to the current field value.
            row = self.qt_model._db_to_row.get(self.field_value, None)
            logger.log(1, "Found row %s for value %s", row, self.field_value)
            if row is not None:
                index = self.qt_model.index(row, 0)
                logger.log(
                    1, "Found index %s for value %s", index, self.field_value
                )
            else:
                logger.log(
                    1,
                    "No row found for value %s",
                    self.field_value,
                )

        # Either select what we have found or clear the selection.
        tree = cast("TreeView", self.popup.tree)
        tree.setCurrentIndex(index)

    def on_item_selected(self, item: "QtRecord"):
        # Handle selection of a record from the popup.
        logger.log(
            1, "%s.on_item_selected(%s)", self.__class__.__name__, item.db_id
        )

        # Update the line edit with the selected record's display text.
        text = item.display_text()
        logger.log(1, "%s.on_item_selected: %s", self.__class__.__name__, text)

        self.line_edit.setText(text)
        self.popup.hide()

        # Store the selected record's database ID as the field value.
        self.field_value = item.db_id

    def _sel_field_value(self, new_value: "None | DBM_O | RecIdType") -> bool:
        """Change the field value.

        The new value can be a database record or an ID of a record.

        Args:
            new_value: The new value to set for the field.

        Returns:
            True if the field value has been changed, False if
            the new value is the same as the old value or we were unable to
            compute the label (in which case we set the field to null).
        """
        assert new_value is not None

        # Convert database record objects to their IDs.
        if hasattr(new_value, "metadata"):
            logger.log(
                1,
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

        # Skip update if the value hasn't changed.
        if new_value == self.field_value:
            logger.log(
                1,
                "%s.change_field_value(): same value: %s",
                self.__class__.__name__,
                new_value,
            )
            return False

        # Change the label.
        label = self.get_record_label(new_value)
        if label == "":
            self.set_to_null()
            return False
        self.line_edit.setText(label)

        # Set value.
        self.qt_model.set_prioritized_ids([new_value])
        self.field_value = new_value
        return True

    def save_value_to(self, record: Any):
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

    def create_ex_field(self) -> "ExField":
        from exdrf.field_types.ref_o2m import RefOneToManyField

        return RefOneToManyField(
            name=self.name,
            description=self.description or "",
            nullable=self.nullable,
            ref=self.qt_model.db_model,  # type: ignore
        )

    def on_record_saved(self, record: DBM_O) -> None:
        """The record has been saved."""
        new_rec_id = self.qt_model.get_db_item_id(record)
        if self._field_value == new_rec_id:
            # Change the label.
            label = self.get_record_label(new_rec_id)
            if label == "":
                return
            self.line_edit.setText(label)
        else:
            self.change_field_value(new_rec_id)

    @top_level_handler
    def on_edit_item(self):
        """Opens the edit dialog for the current item."""
        if self._field_value is None:
            from exdrf_qt.controls.toast import Toast

            Toast.show_error(
                self,
                self.t(
                    "cmn.no_selection",
                    "No selection",
                ),
            )
            return

        # Create the editor widget.
        editor = self.create_editor(record_id=self._field_value)
        if editor is None:
            return

        # Start the editing.
        editor.on_begin_edit()
