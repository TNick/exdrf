import logging
from datetime import datetime, timezone
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

from exdrf.constants import RecIdType
from exdrf.var_bag import VarBag
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QDialogButtonBox,
    QMessageBox,
    QPushButton,
    QStyle,
    QWidget,
)
from sqlalchemy import select

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.field_ed.base import DrfFieldEd
from exdrf_qt.utils.tlh import top_level_handler

if TYPE_CHECKING:
    from sqlalchemy import Select  # noqa: F401
    from sqlalchemy.orm import Session  # noqa: F401

    from exdrf_qt.context import QtContext  # noqa: F401

DBM = TypeVar("DBM")
logger = logging.getLogger(__name__)


class ExdrfEditorBase(QWidget, QtUseContext):
    """A widget that allows the user to edit a set of fields.

    The ExdrfEditor class allows you to edit a database record. This class
    is more flexible than this class and allows you to edit a set of fields
    that are not part of a database record.

    Attributes:
        edit_fields: A list of field editors used to edit the record. The
            constructor enumerates the controls and adds to this list all
            controls that are instances of `DrfFieldEd`.
        _is_dirty: A boolean indicating if the record has been modified.
        _is_editing: A boolean indicating if the widget is in editing mode
            or in view mode.

    Signals:
        dirtyChanged: Emitted when the dirty state changes.
        editingChanged: Emitted when the widget switches between the editor role
            and the viewer role.
        editorCleared: Emitted when the editor is cleared.
        controlChanged: Emitted when a component control changes.
        enteredErrorState: Emitted when one of the component controls enters
            the error state.
    """

    edit_fields: List["DrfFieldEd"]
    _is_dirty: bool = False
    _is_editing: bool = False

    dirtyChanged = pyqtSignal(bool)
    editingChanged = pyqtSignal(bool)
    editorCleared = pyqtSignal()
    controlChanged = pyqtSignal()
    enteredErrorState = pyqtSignal(str)

    def __init__(
        self,
        ctx: "QtContext",
        parent: Optional["QWidget"] = None,
    ):
        logger.debug("__init__")

        self.ctx = ctx
        super().__init__(parent=parent)

        # Prepare widgets loaded from UI file.
        if hasattr(self, "setup_ui"):
            self.setup_ui(self)

        # Find fields to edit.
        self.edit_fields = self.detect_edit_fields()

        # Connect editors.
        for w in self.edit_fields:
            self.install_editor(w)

        logger.debug(
            "ExdrfEditorBase has been initialized with %d fields",
            len(self.edit_fields),
        )

    def detect_edit_fields(self):
        """Detect the fields to edit.

        The default implementation assumes a method named `enum_controls` is
        defined in the subclass. This method should return a list of widgets
        which this method will add to the `edit_fields` list if they are
        instances of `DrfFieldEd`. The `exdrf_qt.scripts.gen_ui_file`
        module can be used to generate _ui.py files from .ui files that
        already have the `enum_controls` method defined.

        Reimplement this method to handle other cases.

        Returns:
            The list of fields to edit.
        """
        return [w for w in self.enum_controls() if isinstance(w, DrfFieldEd)]

    def install_editor(self, fld_editor: "DrfFieldEd"):
        """Install a field editor into the form.

        Args:
            fld_editor: The field editor to install.
        """
        logger.debug(
            "install_editor %s (id %s)",
            fld_editor.name,
            id(fld_editor),
        )

        # Connect the change signal from each field editor.
        controlChanged = getattr(fld_editor, "controlChanged", None)
        if controlChanged is not None:
            controlChanged.connect(self.set_dirty)
        else:
            logger.warning(
                "Control %s does not have a controlChanged signal",
                fld_editor.__class__.__name__,
            )

        # The error state signal is connected to the editor's own error state
        # signal.
        enteredErrorState = getattr(fld_editor, "enteredErrorState", None)
        if enteredErrorState is not None:
            enteredErrorState.connect(lambda x: self.enteredErrorState.emit(x))
        else:
            logger.warning(
                "Control %s does not have an enteredErrorState signal",
                fld_editor.__class__.__name__,
            )

        # Inform the field editor that it is part of this form.
        fld_editor.set_form(self)

        logger.debug(
            "install_editor done for %s",
            fld_editor.name,
        )

    @property
    def is_dirty(self) -> bool:
        """True if the record has been modified in this editor."""
        return self._is_dirty

    @is_dirty.setter  # type: ignore
    def is_dirty(self, value: bool):
        prev_val = self._is_dirty
        if not self._is_editing:
            self._is_dirty = False
        else:
            self._is_dirty = value

        # Allow subclasses to handle dirty state changes.
        self.dirty_changed(self._is_dirty)

        # Inform interested parties about the dirty state change.
        if prev_val != self._is_dirty:
            logger.debug(
                "is_dirty changed to %s",
                self._is_dirty,
            )
            self.dirtyChanged.emit(self._is_dirty)

    def set_dirty(self):
        """Set the dirty flag to True."""
        self._is_dirty = True
        self.controlChanged.emit()

    def dirty_changed(self, value: bool):
        """Reimplement this method to handle dirty state changes.

        The default implementation does nothing.

        Args:
            value: The new dirty state.
        """

    def is_valid(self) -> bool:
        """Check if the editor is valid.

        The default implementation checks if all field editors are valid.
        Reimplement this method to handle other cases.

        Returns:
            True if the editor is valid.
        """
        logger.debug("Checking the validity of the editor's content")

        valid = True
        for ed in self.edit_fields:
            if not ed.is_valid():
                valid = False
                logger.debug("Field %s is not valid", ed.name)

        logger.debug(
            "The editor content is %s",
            "valid" if valid else "not valid",
        )
        return valid

    @property
    def is_editing(self) -> bool:
        """True if the widget is in editing mode."""
        return self._is_editing

    @is_editing.setter
    def is_editing(self, value: bool):
        self._is_editing = value
        self.editing_changed(value)
        self.editingChanged.emit(value)

    @property
    def is_top_editor(self) -> bool:
        """True if the widget is the top-level editor.

        The top editor is the one that is expected to create a new record into
        the database or to save the changes to the records in the database.
        A dependent editor is one that is requested to create a new record
        from a relational field. The record that it creates is not saved
        into the database by the editor; it will be associated with the
        parent record and saved to the database by sqlalchemy implicitly.

        A dependent editor also hides the field or fields that point to the
        parent record, as that association is implicit.
        """
        return self.parent_form is None

    def editing_changed(self, value: bool):
        """Reimplement this method to handle edit/view state changes.

        The default implementation goes through all the field editors and
        calls their `change_edit_mode` method to change the edit mode of the
        field editors.

        Args:
            value: True if the editor is in editing mode, False if it is
                in view mode.
        """
        for ed_fld in self.edit_fields:
            ed_fld.change_edit_mode(value)  # type: ignore
        logger.debug(
            "editing_changed to %s",
            value,
        )

    def _clear_editor(self):
        """Clear the editor.

        Do not use this function directly. Use the `on_create_new` method
        instead.
        """
        self.record_id = None
        self.populate(None)
        self.is_dirty = False
        self.editorCleared.emit()
        logger.debug(
            "ExdrfEditorBase has been cleared",
        )
        return self

    def validate_cancel(self) -> bool:
        """Cancel the editing.

        If the widget is in editing mode and there are unsaved changes, the
        user will be prompted to save the changes.

        Returns:
            True if the editing was canceled.
        """
        if not self.is_editing:
            logger.debug(
                "validate_cancel: not editing",
            )
            return True

        if self.is_dirty:
            logger.debug("validate_cancel: state is dirty, asking the user")
            response = QMessageBox.question(
                None,
                self.t(
                    "cmn.cancel-edit.t",
                    "CThe form has unsaved changes",
                ),
                self.t(
                    "cmn.cancel-edit.q",
                    "Do you want to save the changes?",
                ),
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save,
            )
            if response == QMessageBox.Cancel:
                logger.debug("validate_cancel: user chose to cancel")
                return False
            if response == QMessageBox.Save:
                if not self.save_edit():
                    logger.debug("validate_cancel: save_edit failed")
                    return False

        logger.debug("validate_cancel: changing to not editing")
        self.is_editing = False
        return True

    def get_data(self) -> Dict[str, Any]:
        """Get the data from the editor.

        The default implementation returns a dictionary of the data from the
        editor.
        """
        return {ed.name: ed.field_value for ed in self.edit_fields}

    def get_var_bag(self) -> "VarBag":
        """Construct a variable bag from the editor.

        The default implementation constructs a variable bag from the editor's
        fields by calling the `create_ex_field` method on each field editor
        and adding the field to the variable bag.

        Returns:
            The variable bag.
        """
        logger.debug("Getting the variable bag from the editor")
        result = VarBag()
        for ed in self.edit_fields:
            result.add_field(ed.create_ex_field(), ed.field_value)

        logger.debug(
            "Variable bag has been constructed with %d fields",
            len(result.fields),
        )
        return result


class ExdrfEditor(ExdrfEditorBase, Generic[DBM]):
    """A widget that allows the user to edit a record.

    Attributes:
        db_model: The database model class that this editor is for.
        selection: The SQLAlchemy Select object used to query the database.
        record_id: The ID of the record being edited.
        btn_box: The button box used to control the editor.
        parent_form: The parent form.
        _is_dirty: A boolean indicating if the record has been modified.
        _is_editing: A boolean indicating if the widget is in editing mode
            or in view mode.

    Signals:
        recordSaved: Emitted when the record is saved.
        recordChanged: Emitted after the editor/viewer has been populated
            with a record.
    """

    db_model: Type[DBM]
    selection: "Select"
    record_id: Union[RecIdType, None]
    btn_box: Optional[QDialogButtonBox] = None
    parent_form: Optional["ExdrfEditor"] = None

    recordSaved = pyqtSignal(object)
    recordChanged = pyqtSignal(object)

    def __init__(
        self,
        ctx: "QtContext",
        db_model: Type[DBM],
        selection: Optional["Select"] = None,
        record_id: Union[RecIdType, None] = None,
        parent: Optional["QWidget"] = None,
    ):
        logger.debug(
            "Creating an ExdrfEditor for %s(id=%s)",
            db_model.__name__,
            record_id,
        )
        super().__init__(parent=parent, ctx=ctx)
        self.db_model = db_model
        self.selection = (
            selection if selection is not None else select(db_model)
        )

        # Populate the editor if a record ID is provided.
        self.record_id = None
        if record_id is not None:
            self.set_record(record_id)

    def read_record(self, session: "Session", record_id: RecIdType) -> DBM:
        """Read a record from the database.

        The default implementation assumes that the record has an `id` field.
        Reimplement this function to handle other cases.

        Args:
            session: The database session.
            record_id: The ID of the record to read.

        Returns:
            The record read from the database.
        """
        result = session.scalar(  # type: ignore
            self.selection.where(self.db_model.id == record_id)  # type: ignore
        )
        logger.debug(
            "Record %s(id=%s) has been read from the database",
            result.__class__.__name__,
            record_id,
        )
        return cast(DBM, result)

    def set_record(self, record_id: Union[RecIdType, None]):
        """Set the record to edit.

        You can provide `None` as the record ID to clear the editor. The
        function will, in turn, call the `populate` method with `None` as the
        record to clear the editor.

        If the record ID is not `None`, the record will be read from the
        database and the editor will be populated with the record data.
        The dirty flag will be cleared.

        Args:
            record_id: The ID of the record to edit. If None, the editor will
                be cleared (for creating a new record).
        """
        logger.debug(
            "Setting the record to edit to %s(id=%s)",
            self.db_model.__name__,
            record_id,
        )

        # Save the new record.
        self.record_id = record_id

        # If the record_id is None, we're clearing the editor.
        if record_id is None:
            logger.debug("Setting the record to None, clearing the editor")
            return self._clear_editor()

        # Load the record from the database and populate the editor.
        try:
            with self.ctx.same_session() as session:
                self.populate(self.read_record(session, record_id))
                self.recordChanged.emit(self.record_id)
            logger.debug(
                "Record %s(id=%s) has been loaded into the editor",
                self.db_model.__name__,
                record_id,
            )
        except Exception as e:
            str_e = str(e) or e.__class__.__name__
            self._clear_editor()
            self.show_error(
                title=self.t("sq.common.error", "Error"),
                message=self.t(
                    "cmn.load-err",
                    "Failed to load the record into the form due to "
                    "following error: {e}",
                    e=str_e,
                ),
            )
            logger.exception("Exception in ExdrfEditor.set_record")

        # Clear the dirty flag.
        self.is_dirty = False

        return self

    def db_record(self, save: bool = True) -> Optional[DBM]:
        """Get the record that is currently being edited updated with
        the data from the editor.

        Args:
            save: True if the record should be saved to the database.
                `post_save()` method will be called if save is True.

        Returns:
            The record that is currently being edited.
        """
        logger.debug(
            "Getting the record that is currently being edited",
            "save=%s",
            save,
        )
        try:
            with self.ctx.same_session() as session:
                if self.record_id is None:
                    # We are dealing with a new record.
                    db_record = self.db_model()
                    new_record = True
                    logger.debug(
                        "Creating a new record for %s",
                        self.db_model.__name__,
                    )
                else:
                    # This is an existing record.
                    db_record = self.read_record(session, self.record_id)
                    new_record = False
                    logger.debug(
                        "Reading an existing record for %s(id=%s)",
                        self.db_model.__name__,
                        self.record_id,
                    )

                # Ask the subclass to populate the record with the data from
                # the editor.
                with session.no_autoflush:
                    self.save_to_record(db_record, new_record, session)

                # Post-process the record.
                if save:
                    self.post_save(session, db_record)

                logger.debug(
                    "Record %s(id=%s) has been updated with the data "
                    "from the editor",
                    self.db_model.__name__,
                    self.record_id,
                )
                return db_record
        except Exception as e:
            str_e = str(e) or e.__class__.__name__
            self.show_error(
                title=self.t("sq.common.error", "Error"),
                message=self.t(
                    "cmn.save-err",
                    "Failed to save the record due to following error: {e}",
                    e=str_e,
                ),
            )
            logger.exception("Exception in ExdrfEditor.on_save")
            return None

    @top_level_handler
    def on_cancel_edit(self):
        """Undo changes and exit edit mode.

        The function asks the user if they want to discard changes (if the
        record has been modified). If the user chooses to discard the changes,
        the editor will be cleared and the view mode will be set.

        The function changes internal mode to `not editing` and reads
        the record from the database to re-populate the editor with
        original data.

        Returns:
            False if the user cancels the operation.
        """
        if not self.validate_cancel():
            return False

        self.is_editing = False
        self.set_record(self.record_id)
        return True

    @top_level_handler
    def on_reset_edit(self):
        """Read the record from the database but remain in edit mode.

        The function leaves the editor in editing mode but reads the record
        from the database to re-populate the editor with the original data.

        Returns:
            False if the user cancels the operation.
        """
        if not self.validate_cancel():
            return False

        self.is_editing = True
        self.set_record(self.record_id)
        return True

    def _populate(self, record: Union[DBM, None], ignore: List[str]):
        """Populate the editor with the record data.

        The default implementation goes through all the field editors and
        calls their `load_value_from` method to populate the editor with the
        record data. The `ignore` parameter is used to ignore certain fields.

        Args:
            record: The record to populate the editor with. If None, the
                editor should be cleared.
            ignore: A list of field names to ignore.
        """
        ignore_s = set(ignore)
        for ed_fld in self.edit_fields:
            if ed_fld.name in ignore_s:
                continue
            ed_fld.load_value_from(record)

    def populate(self, record: Union[DBM, None]):
        """Populate the widget with the record data.

        Reimplement this method to populate the widget with the record data.

        Args:
            record: The record to populate the widget with. If None, the
                widgets should be cleared.
        """
        raise NotImplementedError(
            "populate() method must be implemented in the subclass."
        )

    def save_to_record(self, record: DBM, is_new: bool, session: "Session"):
        """Save the widget data to the record.

        Reimplement this method to save the widget data to the record.

        Args:
            record: The record to save the data to.
            is_new: True if the record is new and should be created in the
                database.
            session: The database session to use for saving the record.
        """
        for ed_fld in self.edit_fields:
            ed_fld.save_value_to(record)

    def get_id_of_record(self, record: DBM) -> RecIdType:
        """Get the ID of a record.

        The default implementation assumes that the record has an `id` field.
        Reimplement this function to handle other cases.

        Returns:
            The record ID.
        """
        return record.id  # type: ignore

    @top_level_handler
    def on_save(self):
        """The user asks us to save the current record.

        Current record can be a new record being created or an existing record
        being edited.

        If the editor is not in editing mode, in order to support a toggle
        button functionality, the editor is switched to editing mode and
        the function returns.

        The function uses the "same session" functionality, meaning that
        a new session is created only if there is no current session. At the end
        of it, if no error occurs, the session is committed.
        """
        if not self.is_editing:
            self.is_editing = True
            return

        self.db_record(save=True)

    def post_save(self, session: "Session", db_record: DBM):
        """Called after the record has been populated with the data from the
        editor.

        The default implementation adds the record to the session and commits
        the session. The editor is moved to the view mode and the record ID is
        updated.

        Emits the `recordSaved` signal.

        Args:
            session: The database session.
            db_record: The record that has been saved.
        """
        session.add(db_record)
        if hasattr(db_record, "updated_on"):
            db_record.updated_on = datetime.now(  # type: ignore[union-attr]
                timezone.utc
            )
        session.commit()
        self.is_editing = False
        self.record_id = self.get_id_of_record(db_record)
        self.recordSaved.emit(db_record)

    @top_level_handler
    def on_begin_view(self):
        """Begin examining the record.

        The function sets the editor to view mode.
        """
        if self.record_id is None:
            return
        assert not self.is_dirty
        self.is_editing = False

    @top_level_handler
    def on_begin_edit(self):
        """Begin editing the record.

        The function sets the editor to editing mode.
        """
        if self.record_id is None:
            return
        assert not self.is_dirty
        self.is_editing = True

    @top_level_handler
    def on_create_new(self):
        """Create a new record.

        The function sets the editor to editing mode and clears the editor.
        """
        if not self.validate_cancel():
            return
        self.is_editing = True
        self._clear_editor()

    @top_level_handler
    def on_create_new_dependent(self, parent_form: "ExdrfEditor"):
        """Prepare the editor to create a new record that will be attached
        to another record.
        """
        self.parent_form = parent_form
        self.on_create_new()

    def create_button_box(self) -> QDialogButtonBox:
        """Create a button box for the editor."""
        result = QDialogButtonBox(
            cast(
                QDialogButtonBox.StandardButtons,
                QDialogButtonBox.StandardButton.Save
                | QDialogButtonBox.StandardButton.Cancel
                | QDialogButtonBox.StandardButton.Discard
                | QDialogButtonBox.StandardButton.Reset,
            ),
            self,
        )

        result.rejected.connect(self.on_cancel_edit)  # type: ignore[union-attr]
        # type: ignore[union-attr]
        result.rejected.connect(lambda: self.close_window(self))

        style = self.style()
        assert style is not None

        discard_btn = result.button(QDialogButtonBox.StandardButton.Discard)
        assert discard_btn is not None
        discard_btn.clicked.connect(self.on_cancel_edit)  # type: ignore
        discard_btn.setIcon(
            style.standardIcon(QStyle.StandardPixmap.SP_DialogDiscardButton)
        )
        discard_btn.setToolTip(
            self.t(
                "cmn.editor.discard.tip",
                "Moves the window to view mode and reads the data from the "
                "database again. Changes are lost.",
            )
        )
        discard_btn.setEnabled(False)

        reset_btn = result.button(QDialogButtonBox.StandardButton.Reset)
        assert reset_btn is not None
        reset_btn.clicked.connect(self.on_reset_edit)  # type: ignore
        reset_btn.setIcon(
            style.standardIcon(QStyle.StandardPixmap.SP_DialogResetButton)
        )
        reset_btn.setToolTip(
            self.t(
                "cmn.editor.reset.tip",
                "Reads the data from the database again and repopulates the "
                "editor. The editor remains in editing mode.",
            )
        )
        reset_btn.setEnabled(False)

        save_btn = result.button(QDialogButtonBox.StandardButton.Save)
        assert save_btn is not None
        save_btn.setIcon(
            style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)
        )
        save_btn.setEnabled(False)
        save_btn.setToolTip(
            self.t(
                "cmn.editor.save.tip",
                "When in edit mode, saves the data to the database and moves "
                "the editor to view mode. When in view mode, moves the editor "
                "to edit mode.",
            )
        )
        save_btn.clicked.connect(self.on_save)  # type: ignore

        cancel_btn = result.button(QDialogButtonBox.StandardButton.Cancel)
        assert cancel_btn is not None
        cancel_btn.setToolTip(
            self.t(
                "cmn.editor.cancel.tip",
                "Cancels all edits and closes the editor.",
            )
        )
        cancel_btn.setIcon(
            style.standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton)
        )

        # When the state of the controls changes we need to update the
        # button box state.
        self.recordSaved.connect(self.bbox_react_to_changes)
        self.controlChanged.connect(self.bbox_react_to_changes)
        self.enteredErrorState.connect(self.bbox_react_to_changes)
        self.editingChanged.connect(self.bbox_react_to_changes)

        self.btn_box = result
        return result

    def style_as_save(self, save_btn: "QPushButton"):
        """Style the button box as a save button.

        Args:
            save_btn: The save button to style.
        """
        style = self.style()
        assert style is not None

        save_btn.setText(
            self.t("cmn.save", "Save")
            if self.is_dirty
            else self.t("cmn.saved", "Saved")
        )
        save_btn.setIcon(
            style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)
        )
        save_btn.setEnabled(self.is_valid() and self.is_dirty)

    def style_as_edit(self, save_btn: "QPushButton"):
        """Style the button box as an edit button.

        Args:
            save_btn: The save button to style.
        """
        style = self.style()
        assert style is not None
        save_btn.setText(self.t("cmn.edit", "Edit"))
        save_btn.setIcon(self.get_icon("edit_button"))
        save_btn.setEnabled(True)

    def bbox_react_to_changes(self):
        """Update the state of the button box."""
        if self.btn_box is None:
            return

        style = self.style()
        assert style is not None

        reset_btn = self.btn_box.button(QDialogButtonBox.StandardButton.Reset)
        assert reset_btn is not None

        save_btn = self.btn_box.button(QDialogButtonBox.StandardButton.Save)
        assert save_btn is not None

        discard_btn = self.btn_box.button(
            QDialogButtonBox.StandardButton.Discard
        )
        assert discard_btn is not None

        if self._is_editing:
            # Plays the role of a save button.
            self.style_as_save(save_btn)

            reset_btn.setEnabled(self._is_dirty)
            discard_btn.setEnabled(self._is_dirty)
        else:
            # Plays the role of a start-edit button.
            self.style_as_edit(save_btn)

            reset_btn.setEnabled(False)
            discard_btn.setEnabled(False)
