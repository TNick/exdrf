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


class _ListEditDialog(QDialog):
    """Popup dialog used to edit list values with type-aware validation.

    The dialog displays a list whose items can be edited in-place and provides
    an input row to add new items. Validation rules depend on the list type.
    """

    def __init__(self, parent: QWidget, value_type: str):
        """Initialize the dialog.

        Args:
            parent: The parent widget.
            value_type: The field type name describing list element type.
        """
        super().__init__(parent)

        # Configure UI elements.
        self.setWindowTitle("Edit List")
        self._value_type = value_type
        self._list = QListWidget(self)
        self._input = QLineEdit(self)
        self._btn_add = QToolButton(self)
        self._btn_rem = QToolButton(self)
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self
        )

        # Set button labels.
        self._btn_add.setText("+")
        self._btn_rem.setText("-")

        # Allow inline editing of items (defaults are acceptable).

        # Apply validators for numeric lists.
        if value_type == FIELD_TYPE_INT_LIST:
            self._input.setValidator(QIntValidator(self))
        elif value_type == FIELD_TYPE_FLOAT_LIST:
            self._input.setValidator(QDoubleValidator(self))

        # Layout assembly.
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

        # Connect signals.
        self._btn_add.clicked.connect(self._on_add)
        self._btn_rem.clicked.connect(self._on_remove)
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)
        self._list.itemChanged.connect(self._on_item_changed)

        # Initial state.
        self._update_ok_enabled()

    def set_values(self, values: List[Any]) -> None:
        """Populate the dialog with an initial list of values.

        Args:
            values: The initial items to display.
        """
        self._list.clear()
        for v in values or []:
            it = QListWidgetItem(str(v))
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsEditable)
            self._list.addItem(it)
        self._update_ok_enabled()

    def values(self) -> List[Any]:
        """Return the current list values, parsed according to type.

        Returns:
            A list containing the parsed items.
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
        """Parse a string according to the configured list element type.

        Args:
            text: The text to parse.

        Returns:
            A tuple (ok, value) where ok indicates whether parsing succeeded.
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
        """Add the value from the input box as a new list item."""
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
        """Remove the currently selected list item, if any."""
        row = self._list.currentRow()
        if row >= 0:
            it = self._list.takeItem(row)
            if it is not None:
                del it
        self._update_ok_enabled()

    def _on_item_changed(self, it: QListWidgetItem) -> None:
        """Validate a list item after it was edited.

        Args:
            it: The item that changed.
        """
        ok, _ = self._parse(it.text())
        it.setBackground(QBrush(QColor("white" if ok else "salmon")))
        self._update_ok_enabled()

    def _all_items_valid(self) -> bool:
        """Check whether all list items are valid according to type.

        Returns:
            True if all items are valid, False otherwise.
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
        """Enable or disable the OK button based on validation state."""
        btn = self._buttons.button(QDialogButtonBox.Ok)
        if btn is not None:
            btn.setEnabled(self._all_items_valid())

    def _on_accept(self) -> None:
        """Accept the dialog only if the list is fully valid."""
        if self._all_items_valid():
            self.accept()
        else:
            self.reject()


class _ListButtonEditor(QToolButton):
    """Tiny editor that opens a popup to edit list-typed values."""

    editingFinished = pyqtSignal()

    def __init__(self, parent: QWidget, value_type: str):
        """Initialize the tool-button editor.

        Args:
            parent: The parent widget.
            value_type: Field type name describing list element type.
        """
        super().__init__(parent)
        self._value_type = value_type
        self._values: List[Any] = []
        self.setText("...")
        self.clicked.connect(self._on_clicked)

    def _on_clicked(self) -> None:
        """Open the list editor dialog and store the result if accepted."""
        dlg = _ListEditDialog(self, self._value_type)
        dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        dlg.set_values(self._values)
        if dlg.exec_() == QDialog.Accepted:
            self._values = dlg.values()
            self.editingFinished.emit()

    def setValues(self, values: List[Any]) -> None:
        """Set the current list value represented by this editor.

        Args:
            values: The list values to store.
        """
        self._values = list(values or [])

    def values(self) -> List[Any]:
        """Get the current list value represented by this editor.

        Returns:
            A copy of the stored list of values.
        """
        return list(self._values)


class VarItemDelegate(QStyledItemDelegate):
    """Delegate that creates editors based on the field type for values."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        ctx: Optional[Any] = None,
    ):
        """Initialize the delegate.

        Args:
            parent: The parent widget.
            ctx: Optional application context (for future use).
        """
        super().__init__(parent)
        self.ctx = ctx

    def paint(
        self,
        painter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        """Paint the item, honoring model-provided background for non-selected rows.

        Args:
            painter: The painter used to draw.
            option: The style option describing the cell.
            index: The index being painted.
        """
        try:
            # Respect model BackgroundRole when not selected/hovered to avoid QSS masking.
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
        """Create an appropriate editor for the model index.

        Args:
            parent: The parent widget for the editor.
            option: Style option for the editor.
            index: The model index to edit (value column only).

        Returns:
            A QWidget editor instance or None if not editable.
        """
        if index.column() != 1:
            return None
        model = cast(Any, index.model())
        try:
            from exdrf_qt.controls.templ_viewer.model import (
                VarModel as _VarModel,  # lazy import
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
        """Populate editor with the current model value.

        Args:
            editor: The created editor widget.
            index: The model index being edited.
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
        """Commit the value from the editor back to the model.

        Args:
            editor: The editor widget.
            model: The target model.
            index: The model index being edited.
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
        """Size and position the editor within the view cell.

        Args:
            editor: The editor widget.
            option: The style option containing geometry.
            index: The model index being edited.
        """
        if editor is None:
            return
        editor.setGeometry(option.rect)

    @staticmethod
    def _list_type_name(tn: str) -> str:
        """Normalize list field type names outside the standard set.

        Args:
            tn: The raw field type name.

        Returns:
            One of the supported list field type names.
        """
        if tn in (
            FIELD_TYPE_INT_LIST,
            FIELD_TYPE_FLOAT_LIST,
            FIELD_TYPE_STRING_LIST,
        ):
            return tn
        return FIELD_TYPE_STRING_LIST

    def _commit_and_close(self, editor: QWidget) -> None:
        """Emit commitData and closeEditor for the given editor.

        Args:
            editor: The editor to commit and close.
        """
        try:
            self.commitData.emit(editor)
        finally:
            try:
                self.closeEditor.emit(editor)  # type: ignore[arg-type]
            except Exception:
                pass
