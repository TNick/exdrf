"""Item delegate for template viewer variables table (value column).

This module provides VarItemDelegate, which creates type-aware editors
for the value column (checkboxes for bool, date/datetime pickers,
validated line edits for int/float, list popup for list types) and
paints model BackgroundRole when not selected. It also defines the
private _ListEditDialog and _ListButtonEditor for list editing.
"""

import logging
from typing import Any, List, Optional, Tuple, cast

from exdrf.constants import (
    FIELD_TYPE_BOOL,
    FIELD_TYPE_DATE,
    FIELD_TYPE_DT,
    FIELD_TYPE_FLOAT,
    FIELD_TYPE_FLOAT_LIST,
    FIELD_TYPE_INT_LIST,
    FIELD_TYPE_INTEGER,
    FIELD_TYPE_STRING_LIST,
)
from PyQt5.QtCore import QModelIndex, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QDoubleValidator, QIntValidator
from PyQt5.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)
VERBOSE = 1


class _ListEditDialog(QDialog):
    """Popup dialog to edit list values with type-aware validation.

    Displays a list of items (editable in-place) and an input row to add
    items. Validation depends on value_type (int list, float list, or
    string list). OK is enabled only when all items parse correctly.

    Attributes:
        _value_type: Field type name for list elements (int/float/string list).
        _list: QListWidget holding the items.
        _input: QLineEdit for new item text.
        _btn_add: Button to add item from _input.
        _btn_rem: Button to remove selected item.
        _buttons: OK/Cancel button box.
    """

    def __init__(self, parent: QWidget, value_type: str) -> None:
        """Initialize the dialog with parent and list element type.

        Args:
            parent: Parent widget for the dialog.
            value_type: Field type name for list elements (e.g. int list,
                float list, string list); used for validators and parsing.
        """
        super().__init__(parent)

        self.setWindowTitle("Edit List")
        self._value_type = value_type
        self._list = QListWidget(self)
        self._input = QLineEdit(self)
        self._btn_add = QToolButton(self)
        self._btn_rem = QToolButton(self)
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self
        )
        self._btn_add.setText("+")
        self._btn_rem.setText("-")

        if value_type == FIELD_TYPE_INT_LIST:
            self._input.setValidator(QIntValidator(self))
        elif value_type == FIELD_TYPE_FLOAT_LIST:
            self._input.setValidator(QDoubleValidator(self))

        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        row.addWidget(self._input, 1)
        row.addWidget(self._btn_add, 0)
        lay.addLayout(row)
        lay.addWidget(self._list, 1)
        row2 = QHBoxLayout()
        row2.addStretch(1)
        row2.addWidget(self._btn_rem)
        lay.addLayout(row2)
        lay.addWidget(self._buttons)

        self._btn_add.clicked.connect(self._on_add)
        self._btn_rem.clicked.connect(self._on_remove)
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)
        self._list.itemChanged.connect(self._on_item_changed)
        self._update_ok_enabled()

    def set_values(self, values: List[Any]) -> None:
        """Populate the list with initial values and update OK state.

        Args:
            values: Initial items to display (each shown as str); None or
                empty list clears the list.
        """
        self._list.clear()
        for v in values or []:
            it = QListWidgetItem(str(v))
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsEditable)
            self._list.addItem(it)
        self._update_ok_enabled()

    def values(self) -> List[Any]:
        """Return the current list values, parsed according to _value_type.

        Invalid items are left as strings. Used when the user accepts
        the dialog.

        Returns:
            List of parsed values (int/float/str per type) or raw strings.
        """
        result: List[Any] = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item is None:
                continue
            text = item.text()
            ok, parsed = self._parse(text)
            if not ok:
                parsed = text
            result.append(parsed)
        return result

    def _parse(self, text: str) -> Tuple[bool, Any]:
        """Parse a string according to _value_type (int/float list or string).

        Args:
            text: Text to parse (e.g. from list item or input line).

        Returns:
            Pair (ok, value): ok True if parsing succeeded, value the
            parsed value or None on failure.
        """
        if self._value_type == FIELD_TYPE_INT_LIST:
            try:
                return True, int(text)
            except Exception:
                logger.error("Error parsing int list", exc_info=True)
                return False, None
        if self._value_type == FIELD_TYPE_FLOAT_LIST:
            try:
                return True, float(text)
            except Exception:
                logger.error("Error parsing float list", exc_info=True)
                return False, None
        return True, text

    def _on_add(self) -> None:
        """Add the input line text as a new list item; highlight if invalid."""
        txt = self._input.text()
        if txt == "":
            return
        ok, _ = self._parse(txt)
        it = QListWidgetItem(txt)
        it.setFlags(it.flags() | Qt.ItemFlag.ItemIsEditable)
        if not ok:
            it.setBackground(QBrush(QColor("salmon")))
        self._list.addItem(it)
        self._input.clear()
        self._update_ok_enabled()

    def _on_remove(self) -> None:
        """Remove the currently selected list item and update OK state."""
        row = self._list.currentRow()
        if row >= 0:
            it = self._list.takeItem(row)
            if it is not None:
                del it
        self._update_ok_enabled()

    def _on_item_changed(self, it: QListWidgetItem) -> None:
        """Validate the item after edit; set background to white or salmon.

        Args:
            it: The list widget item that was changed.
        """
        ok, _ = self._parse(it.text())
        it.setBackground(QBrush(QColor("white" if ok else "salmon")))
        self._update_ok_enabled()

    def _all_items_valid(self) -> bool:
        """Return whether every list item parses successfully for _value_type.

        Returns:
            True if all items parse, False if any fail.
        """
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item is None:
                continue
            ok, _ = self._parse(item.text())
            if not ok:
                return False
        return True

    def _update_ok_enabled(self) -> None:
        """Enable OK only when _all_items_valid is true."""
        btn = self._buttons.button(QDialogButtonBox.Ok)
        if btn is not None:
            btn.setEnabled(self._all_items_valid())

    def _on_accept(self) -> None:
        """Accept the dialog only when all items are valid; else reject."""
        if self._all_items_valid():
            self.accept()
        else:
            self.reject()


class _ListButtonEditor(QToolButton):
    """Tool button that opens _ListEditDialog to edit list-typed values.

    Shows "..." as label; on click opens the dialog and emits
    editingFinished when the user accepts. Values are stored in _values.

    Attributes:
        _value_type: Field type name for list elements (passed to dialog).
        _values: Current list value (edited in dialog, committed on accept).
    """

    editingFinished = pyqtSignal()

    def __init__(self, parent: QWidget, value_type: str) -> None:
        """Initialize the list button editor.

        Args:
            parent: Parent widget for the button.
            value_type: Field type name for list elements (int/float/string
                list); passed to _ListEditDialog for validation.
        """
        super().__init__(parent)
        self._value_type = value_type
        self._values: List[Any] = []
        self.setText("...")
        self.clicked.connect(self._on_clicked)

    def _on_clicked(self) -> None:
        """Open the list editor dialog; on accept update _values and emit."""
        dlg = _ListEditDialog(self, self._value_type)
        dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        dlg.set_values(self._values)
        if dlg.exec_() == QDialog.Accepted:
            self._values = dlg.values()
            self.editingFinished.emit()

    def setValues(self, values: List[Any]) -> None:
        """Set the list value shown when the dialog opens.

        Args:
            values: List to store (None or non-sequence becomes empty list).
        """
        self._values = list(values or [])

    def values(self) -> List[Any]:
        """Return a copy of the current list value (after dialog accept).

        Returns:
            Copy of _values for commit to model.
        """
        return list(self._values)


class VarItemDelegate(QStyledItemDelegate):
    """Delegate that creates type-aware editors for the value column.

    For VarModel value column (column 1): checkboxes for bool, date/
    datetime pickers, validated line edits for int/float, list popup
    for list types, else plain line edit. Paints model BackgroundRole
    when the cell is not selected or hovered.

    Attributes:
        ctx: Optional application context (for future use).
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        ctx: Optional[Any] = None,
    ) -> None:
        """Initialize the delegate.

        Args:
            parent: Optional parent widget for the delegate.
            ctx: Optional application context (e.g. for translation).
        """
        super().__init__(parent)
        self.ctx = ctx

    def paint(
        self,
        painter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        """Paint the cell; use model BackgroundRole when not selected/hovered.

        Fills the cell rect with the model's background brush before
        calling the base paint so custom backgrounds are visible.

        Args:
            painter: Painter to use for drawing.
            option: Style option for the cell (rect, state).
            index: Model index of the cell.
        """
        try:
            is_selected = bool(option.state & QStyle.State_Selected)
            is_hover = bool(option.state & QStyle.State_MouseOver)
            if not is_selected and not is_hover:
                mdl = cast(Any, index.model())
                back = mdl.data(index, Qt.ItemDataRole.BackgroundRole)
                if isinstance(back, QBrush):
                    painter.save()
                    painter.fillRect(option.rect, back)
                    painter.restore()
        except Exception:
            logger.error("Error painting item", exc_info=True)
        super().paint(painter, option, index)

    def createEditor(
        self,
        parent: Optional[QWidget],
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> Optional[QWidget]:
        """Create a type-appropriate editor for the value column.

        Returns None for non-value columns. For value column: list
        button for list types, checkbox for bool, date/datetime edit,
        validated line edit for int/float, else plain line edit.

        Args:
            parent: Parent widget for the editor.
            option: Style option (unused for type choice).
            index: Model index; must be value column (1) for an editor.

        Returns:
            Editor widget or None if column is not 1.
        """
        if index.column() != 1:
            return None
        model = cast(Any, index.model())
        try:
            from exdrf_qt.controls.templ_viewer.model import (
                VarModel as _VarModel,
            )

            var_model = cast(_VarModel, model)
            row = index.row()
            field = var_model.filtered_bag.fields[row]
            t = field.type_name

            if field.is_list or t in (
                FIELD_TYPE_STRING_LIST,
                FIELD_TYPE_INT_LIST,
                FIELD_TYPE_FLOAT_LIST,
            ):
                par = cast(QWidget, parent) if parent is not None else QWidget()
                ed = _ListButtonEditor(par, self._list_type_name(t))
                ed.editingFinished.connect(lambda: self._commit_and_close(ed))
                return ed

            if t == FIELD_TYPE_BOOL:
                return QCheckBox(parent)
            if t == FIELD_TYPE_INTEGER:
                edit = QLineEdit(parent)
                edit.setValidator(QIntValidator(parent))
                return edit
            if t == FIELD_TYPE_FLOAT:
                edit = QLineEdit(parent)
                edit.setValidator(QDoubleValidator(parent))
                return edit
            if t == FIELD_TYPE_DATE:
                de = QDateEdit(parent)
                de.setCalendarPopup(True)
                return de
            if t == FIELD_TYPE_DT:
                dte = QDateTimeEdit(parent)
                dte.setCalendarPopup(True)
                return dte
            return QLineEdit(parent)
        except Exception:
            logger.error("Error creating editor", exc_info=True)
            return QLineEdit(parent)

    def setEditorData(
        self, editor: Optional[QWidget], index: QModelIndex
    ) -> None:
        """Load the current model value into the editor.

        Dispatches by editor type: list button, checkbox, date/datetime
        edit, or line edit. Does nothing if editor is None or not value column.

        Args:
            editor: Editor widget created by createEditor.
            index: Model index being edited (value column).
        """
        if editor is None or index.column() != 1:
            return
        mdl = cast(Any, index.model())
        value = mdl.data(index, Qt.ItemDataRole.EditRole)

        if isinstance(editor, _ListButtonEditor):
            seq = list(value) if isinstance(value, (list, tuple)) else []
            editor.setValues(seq)
            return

        if isinstance(editor, QCheckBox):
            editor.setChecked(bool(value))
            return

        if isinstance(editor, QDateEdit):
            try:
                from datetime import date as _date

                if isinstance(value, _date):
                    editor.setDate(value)  # type: ignore[arg-type]
            except Exception:
                logger.error("Error setting date", exc_info=True)
            return

        if isinstance(editor, QDateTimeEdit):
            try:
                from datetime import datetime as _dt

                if isinstance(value, _dt):
                    editor.setDateTime(value)  # type: ignore[arg-type]
            except Exception:
                logger.error("Error setting date time", exc_info=True)
            return

        if isinstance(editor, QLineEdit):
            editor.setText("" if value is None else str(value))

    def setModelData(
        self,
        editor: Optional[QWidget],
        model: Any,
        index: QModelIndex,
    ) -> None:
        """Write the editor value back to the model at the given index.

        Dispatches by editor type; for line edit, uses field type to
        parse int/float or pass string. Does nothing if editor is None
        or not value column.

        Args:
            editor: Editor widget that holds the new value.
            model: Model to update (VarModel).
            index: Model index being edited (value column).
        """
        if editor is None or index.column() != 1:
            return

        if isinstance(editor, _ListButtonEditor):
            model.setData(index, editor.values(), Qt.ItemDataRole.EditRole)
            return

        if isinstance(editor, QCheckBox):
            model.setData(
                index,
                bool(editor.isChecked()),
                Qt.ItemDataRole.EditRole,
            )
            return

        if isinstance(editor, QDateEdit):
            model.setData(
                index,
                editor.date().toPyDate(),
                Qt.ItemDataRole.EditRole,
            )
            return

        if isinstance(editor, QDateTimeEdit):
            model.setData(
                index,
                editor.dateTime().toPyDateTime(),
                Qt.ItemDataRole.EditRole,
            )
            return

        if isinstance(editor, QLineEdit):
            text = editor.text()
            try:
                from exdrf_qt.controls.templ_viewer.model import (
                    VarModel as _VarModel,
                )

                var_model = cast(_VarModel, index.model())
                field = var_model.filtered_bag.fields[index.row()]
                t = field.type_name

                # Parse line edit text by field type before committing
                if t == FIELD_TYPE_INTEGER:
                    model.setData(
                        index,
                        int(text) if text != "" else None,
                        Qt.ItemDataRole.EditRole,
                    )
                    return

                if t == FIELD_TYPE_FLOAT:
                    model.setData(
                        index,
                        float(text) if text != "" else None,
                        Qt.ItemDataRole.EditRole,
                    )
                    return

                model.setData(index, text, Qt.ItemDataRole.EditRole)
                return
            except Exception:
                logger.error("Error setting text", exc_info=True)
                model.setData(index, text, Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(
        self,
        editor: Optional[QWidget],
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        """Set the editor geometry to the cell rect from the option.

        Args:
            editor: Editor widget to position (ignored if None).
            option: Style option whose rect is used for geometry.
            index: Model index (unused).
        """
        if editor is None:
            return
        editor.setGeometry(option.rect)

    @staticmethod
    def _list_type_name(tn: str) -> str:
        """Return a supported list type name for the given field type.

        Args:
            tn: Field type name (e.g. from VarModel field).

        Returns:
            Same string if int/float/string list, else string list.
        """
        if tn in (
            FIELD_TYPE_INT_LIST,
            FIELD_TYPE_FLOAT_LIST,
            FIELD_TYPE_STRING_LIST,
        ):
            return tn
        return FIELD_TYPE_STRING_LIST

    def _commit_and_close(self, editor: QWidget) -> None:
        """Emit commitData then closeEditor for the list button editor.

        Called when _ListButtonEditor emits editingFinished. Ensures
        closeEditor is emitted even if commitData raises.

        Args:
            editor: Editor widget to commit and close.
        """
        try:
            self.commitData.emit(editor)
        finally:
            try:
                self.closeEditor.emit(editor)  # type: ignore[arg-type]
            except Exception:
                logger.log(
                    VERBOSE,
                    "Error emitting closeEditor for list editor",
                    exc_info=True,
                )
