import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Generic, Optional, Type, TypeVar, Union

from exdrf.constants import RecIdType
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QMessageBox, QWidget
from sqlalchemy import select

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from sqlalchemy import Select  # noqa: F401
    from sqlalchemy.orm import Session  # noqa: F401

    from exdrf_qt.context import QtContext  # noqa: F401

DBM = TypeVar("DBM")
logger = logging.getLogger(__name__)


class EditorDb(QWidget, QtUseContext, Generic[DBM]):
    """A widget that allows the user to edit a database record.

    Attributes:
        db_model: The database model class that this editor is for.
        selection: The SQLAlchemy Select object used to query the database.
        _is_dirty: A boolean indicating if the record has been modified.
        _is_editing: A boolean indicating if the widget is in editing mode
            or in view mode.
    """

    db_model: Type[DBM]
    selection: "Select"
    record_id: Union[RecIdType, None]

    _is_dirty: bool = False
    _is_editing: bool = False

    recordSaved = pyqtSignal(object)
    dirtyChanged = pyqtSignal(bool)
    editingChanged = pyqtSignal(bool)
    editorCleared = pyqtSignal()
    recordChanged = pyqtSignal(object)
    recordSaved = pyqtSignal(object)

    def __init__(
        self,
        ctx: "QtContext",
        db_model: Type[DBM],
        selection: Optional["Select"] = None,
        record_id: Union[RecIdType, None] = None,
        parent: Optional["QWidget"] = None,
    ):
        super().__init__(parent=parent)
        self.ctx = ctx
        self.db_model = db_model
        self.selection = (
            selection if selection is not None else select(db_model)
        )

        # Populate the editor if a record ID is provided.
        self.record_id = None
        if record_id is not None:
            self.set_record(record_id)

    @property
    def is_dirty(self) -> bool:
        """True if the record has been modified in this editor."""
        return self._is_dirty

    @is_dirty.setter
    def is_dirty(self, value: bool):
        if not self._is_editing:
            self._is_dirty = False
        else:
            self._is_dirty = value
        self.dirty_changed(self._is_dirty)
        self.dirtyChanged.emit(self._is_dirty)

    def dirty_changed(self, value: bool):
        """Reimplement this method to handle dirty state changes."""

    @property
    def is_editing(self) -> bool:
        """True if the widget is in editing mode."""
        return self._is_editing

    @is_editing.setter
    def is_editing(self, value: bool):
        self._is_editing = value
        self.editing_changed(value)
        self.editingChanged.emit(value)

    def editing_changed(self, value: bool):
        """Reimplement this method to handle edit/view state changes."""

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
        return session.scalar(
            self.selection.where(
                self.db_model.id == record_id  # type: ignore[operator]
            )
        )

    def _clear_editor(self):
        """Clear the editor."""
        self.db_id = None
        self.populate(None)
        self.is_dirty = False
        self.editorCleared.emit()
        return self

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
        # Save the new record.
        self.db_id = record_id

        # If the record_id is None, we're clearing the editor.
        if record_id is None:
            return self._clear_editor()

        # Load the record from the database and populate the editor.
        try:
            with self.ctx.same_session() as session:
                self.populate(self.read_record(session, record_id))
                self.recordChanged.emit(self.db_id)
        except Exception as e:
            str_e = str(e) or e.__class__.__name__
            self._clear_editor()
            self.show_error(
                title=self.t("sq.common.error", "Error"),
                message=self.t(
                    "sq.cn.common.load-err",
                    "Failed to load the record into the form due to "
                    "following error: {e}",
                    e=str_e,
                ),
            )
            logger.exception("Exception in EditorDb.set_record")

        # Clear the dirty flag.
        self.is_dirty = False

        return self

    def validate_cancel(self) -> bool:
        """Cancel the editing.

        If the widget is in editing mode and there are unsaved changes, the
        user will be prompted to save the changes.

        Returns:
            True if the editing was canceled.
        """
        if not self.is_editing:
            return True

        if self.is_dirty:
            response = QMessageBox.question(
                None,
                self.t(
                    "sq.cn.common.cancel-edit.t",
                    "CThe form has unsaved changes",
                ),
                self.t(
                    "sq.cn.common.cancel-edit.q",
                    "Do you want to save the changes?",
                ),
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save,
            )
            if response == QMessageBox.Cancel:
                return False
            if response == QMessageBox.Save:
                if not self.save_edit():
                    return False

        self.is_editing = False
        return True

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
        self.set_record(self.db_id)
        return True

    def on_discard_edit(self):
        """Read the record from the database but remain in edit mode.

        The function leaves the editor in editing mode but reads the record
        from the database to re-populate the editor with the original data.

        Returns:
            False if the user cancels the operation.
        """
        if not self.validate_cancel():
            return False

        self.is_editing = True
        self.set_record(self.db_id)
        return True

    def populate(self, record: Union[DBM, None]):
        """Populate the widget with the record data.

        Reimplement this method to populate the widget with the record data.

        Args:
            record: The record to populate the widget with. If None, the
                widgets should be cleared.
        """
        raise NotImplementedError

    def save_to_record(self, record: DBM, is_new: bool, session: "Session"):
        """Save the widget data to the record.

        Reimplement this method to save the widget data to the record.

        Args:
            record: The record to save the data to.
            is_new: True if the record is new and should be created in the
                database.
            session: The database session to use for saving the record.
        """
        raise NotImplementedError

    def get_id_of_record(self, record: DBM) -> RecIdType:
        """Get the ID of a record.

        The default implementation assumes that the record has an `id` field.
        Reimplement this function to handle other cases.

        Returns:
            The record ID.
        """
        return record.id  # type: ignore[union-attr]

    def on_save(self) -> bool:
        """The user asks us to save the record.

        This can be a new record being created or an existing record being
        edited.
        """
        if not self.is_editing:
            return False

        try:
            with self.ctx.same_session() as session:
                if self.db_id is None:
                    # We are dealing with a new record.
                    db_record = self.db_model()
                    new_record = True
                else:
                    # This is an existing record.
                    db_record = self.read_record(session, self.db_id)
                    new_record = False

                # Ask the subclass to save the data to the record.
                self.save_to_record(db_record, new_record, session)

                # Post-process the record.
                self.post_save(session, db_record)
                return True
        except Exception as e:
            str_e = str(e) or e.__class__.__name__
            self.show_error(
                title=self.t("sq.common.error", "Error"),
                message=self.t(
                    "sq.cn.common.save-err",
                    "Failed to save the record due to following error: {e}",
                    e=str_e,
                ),
            )
            logger.exception("Exception in EditorDb.on_save")
            return False

    def post_save(self, session: "Session", db_record: DBM):
        """Called after the record has been saved."""
        session.add(db_record)
        if hasattr(db_record, "updated_on"):
            db_record.updated_on = datetime.now(  # type: ignore[union-attr]
                timezone.utc
            )
        session.commit()
        self.is_editing = False
        self.db_id = self.get_id_of_record(db_record)
        self.recordSaved.emit(db_record)

    def on_begin_edit(self):
        """Begin editing the record.

        The function sets the editor to editing mode.
        """
        if self.is_editing:
            return
        if self.db_id is None:
            return
        assert not self.is_dirty
        self.is_editing = True

    def on_create_new(self):
        """Create a new record.

        The function sets the editor to editing mode and clears the editor.
        """
        if not self.validate_cancel():
            return
        self.is_editing = True
        self._clear_editor()
