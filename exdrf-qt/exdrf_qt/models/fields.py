import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

import humanize
from attrs import define, field
from exdrf.api import (
    BlobField,
    BoolField,
    DateField,
    DateTimeField,
    DurationField,
    EnumField,
    FilterField,
    FloatField,
    FloatListField,
    FormattedField,
    IntField,
    IntListField,
    RefManyToManyField,
    RefManyToOneField,
    RefOneToManyField,
    RefOneToOneField,
    SortField,
    StrField,
    StrListField,
    TimeField,
)
from exdrf.constants import RecIdType
from exdrf.moment import MomentFormat
from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtGui import QBrush
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QPlainTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import inspect
from sqlalchemy.orm import class_mapper

from exdrf_qt.field_ed.api import (
    DrfBlobEditor,
    DrfBoolEditor,
    DrfDateEditor,
    DrfDateTimeEditor,
    DrfEnumEditor,
    DrfIntEditor,
    DrfLineEditor,
    DrfRealEditor,
    DrfSelMultiEditor,
    DrfSelOneEditor,
    DrfTextEditor,
    DrfTimeEditor,
)
from exdrf_qt.field_ed.base import DrfFieldEd
from exdrf_qt.models.field import (
    DBM,
    NO_EDITOR_VALUE,
    QtField,
    italic_font,
    light_grey,
    regular_font,
)

if TYPE_CHECKING:
    from exdrf.filter import FieldFilter

    from exdrf_qt.models.selector import Selector

logger = logging.getLogger(__name__)


def _resolve_ref_item(session, model_cls, value: Any) -> Any:
    """Resolve a reference value to a database record.

    Args:
        session: The active SQLAlchemy session.
        model_cls: The related model class to load.
        value: The value to resolve (record or ID).

    Returns:
        The resolved database record or None if not found.
    """
    if value is None:
        return None
    if hasattr(value, "metadata"):
        return value
    return session.get(model_cls, value)


def _resolve_ref_list(session, model_cls, values: Any) -> List[Any]:
    """Resolve a list of reference values to database records.

    Args:
        session: The active SQLAlchemy session.
        model_cls: The related model class to load.
        values: Iterable of IDs or records.

    Returns:
        A list of resolved database records.
    """
    if values is None:
        return []
    result: List[Any] = []
    for value in values:
        record = _resolve_ref_item(session, model_cls, value)
        if record is None:
            logger.error(
                "Related record %s not found for model %s",
                value,
                model_cls,
            )
            continue
        result.append(record)
    return result


def _identity_value(item: Any) -> Any:
    """Extract the identity for a SQLAlchemy instance without loading it."""
    try:
        state = inspect(item)
    except Exception:
        logger.log(1, "Failed to inspect value %s", item, exc_info=True)
        return None
    if state is None or state.identity is None:
        return None
    if isinstance(state.identity, (list, tuple)) and len(state.identity) == 1:
        return state.identity[0]
    return state.identity


def _finalize_editor(
    editor: DrfFieldEd,
    nullable: bool,
    read_only: bool,
    description: Optional[str] = None,
) -> None:
    """Apply common editor flags after initialization.

    Args:
        editor: The editor instance to finalize.
        nullable: Whether the editor should allow NULL values.
        read_only: Whether the editor should be read only.
    """
    if description is not None:
        editor.description = description
        if hasattr(editor, "apply_description"):
            editor.apply_description()  # type: ignore[attr-defined]
    editor.nullable = nullable
    editor.read_only = read_only


@define(slots=False)
class QtBlobField(BlobField, QtField[DBM]):
    def create_editor(self, parent) -> Optional[DrfBlobEditor]:
        """Create an editor widget for inline editing."""
        editor = DrfBlobEditor(
            ctx=self.ctx,
            parent=parent,
            name=self.name,
            description="",
            nullable=False,
        )
        _finalize_editor(
            editor, self.nullable, self.read_only, self.description or ""
        )
        return editor

    def configure_editor(self, editor, commit_cb) -> None:
        """Attach signals to the editor for inline editing."""
        if hasattr(editor, "controlChanged"):

            def _on_change() -> None:
                if hasattr(editor, "validate_control"):
                    result = editor.validate_control()
                    if hasattr(result, "is_valid") and not result.is_valid:
                        return
                commit_cb(editor)

            editor.controlChanged.connect(_on_change)

    def values(self, record: DBM) -> Dict[Qt.ItemDataRole, Any]:
        value = getattr(record, self.name)
        if value is None:
            return self.expand_value(None)

        label = self.t("cmn.blob", "BLOB")
        description = self.t(
            "cmn.blob_tip",
            "Binary data ({sz} bytes, {mime})",
            sz=len(value),
            mime=self.mime_type or "application/octet-stream",
        )
        return self.expand_value(
            value,
            FontRole=italic_font,
            ForegroundRole=light_grey,
            AccessibleTextRole=label,
            DisplayRole=label,
            ToolTipRole=description,
            StatusTipRole=description,
            TextAlignmentRole=(
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            ),
            SizeHintRole=QSize(24, 24),
        )


@define
class QtBoolField(BoolField, QtField[DBM]):
    def create_editor(self, parent) -> Optional[QWidget]:
        """Create an editor widget for inline editing."""
        wrapper = _OpaqueCellEditor(parent)
        editor = DrfBoolEditor(
            ctx=self.ctx,
            parent=wrapper,
            name=self.name,
            description=self.description or "",
            nullable=False,
            true_str=self.true_str,
            false_str=self.false_str,
        )
        _finalize_editor(
            editor, self.nullable, self.read_only, self.description or ""
        )
        editor.setStyleSheet("QCheckBox { background: transparent; }")
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(editor)
        wrapper.setLayout(layout)
        wrapper._inner_editor = editor  # type: ignore[attr-defined]
        return wrapper

    def configure_editor(self, editor, commit_cb) -> None:
        """Attach signals to the editor for inline editing."""
        inner = cast(Any, getattr(editor, "_inner_editor", editor))
        if hasattr(inner, "stateChanged"):
            inner.stateChanged.connect(lambda: commit_cb(editor))

    def set_editor_data(self, editor, value: Any) -> None:
        """Populate the editor with the current value."""
        inner = cast("QWidget", getattr(editor, "_inner_editor", editor))
        super().set_editor_data(inner, value)

    def editor_value(self, editor) -> Any:
        """Extract the value from the editor."""
        inner = cast("QWidget", getattr(editor, "_inner_editor", editor))
        return super().editor_value(inner)

    def values(self, record: DBM) -> Dict[Qt.ItemDataRole, Any]:
        value = getattr(record, self.name)
        if value is None:
            return self.expand_value(None)
        return self.expand_value(
            value=value,
            DisplayRole=self.true_str if value else self.false_str,
            EditRole=value,
            ForegroundRole=QBrush(
                Qt.GlobalColor.blue if value else Qt.GlobalColor.red
            ),
        )


@define
class QtDateTimeField(QtField[DBM], DateTimeField):  # type: ignore
    formatter: Optional[MomentFormat] = field(default=None)

    def create_editor(self, parent) -> Optional[DrfDateTimeEditor]:
        """Create an editor widget for inline editing."""
        editor = DrfDateTimeEditor(
            ctx=self.ctx,
            parent=parent,
            name=self.name,
            description="",
            nullable=False,
            format=self.format,
        )
        _finalize_editor(
            editor, self.nullable, self.read_only, self.description or ""
        )
        return editor

    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        value = getattr(record, self.name)  # type: ignore[assignment]
        if value is None:
            return self.expand_value(None)  # type: ignore[no-untyped-call]

        if self.formatter is None:
            self.formatter = MomentFormat.from_string(
                self.format
            )  # type: ignore[assignment]

        display = self.formatter.moment_to_string(value)
        return self.expand_value(  # type: ignore[no-untyped-call]
            value=value,
            DisplayRole=display,
            EditRole=value,
            ToolTipRole=humanize.naturaltime(value),
        )


@define
class QtDateField(DateField, QtField[DBM]):
    formatter: Optional[MomentFormat] = field(default=None)

    def create_editor(self, parent) -> Optional[DrfDateEditor]:
        """Create an editor widget for inline editing."""
        editor = DrfDateEditor(
            ctx=self.ctx,
            parent=parent,
            name=self.name,
            description="",
            nullable=False,
            format=self.format,
        )
        _finalize_editor(
            editor, self.nullable, self.read_only, self.description or ""
        )
        return editor

    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        value = getattr(record, self.name)  # type: ignore[assignment]
        if value is None:
            return self.expand_value(None)  # type: ignore[no-untyped-call]

        if self.formatter is None:
            self.formatter = MomentFormat.from_string(
                self.format
            )  # type: ignore[assignment]

        display = self.formatter.moment_to_string(value)
        return self.expand_value(  # type: ignore[no-untyped-call]
            value=value,
            DisplayRole=display,
            EditRole=value,
            ToolTipRole=humanize.naturaldate(value),
        )


@define
class QtTimeField(TimeField, QtField[DBM]):
    formatter: Optional[MomentFormat] = field(default=None)

    def create_editor(self, parent) -> Optional[DrfTimeEditor]:
        """Create an editor widget for inline editing."""
        editor = DrfTimeEditor(
            ctx=self.ctx,
            parent=parent,
            name=self.name,
            description="",
            nullable=False,
            format=self.format,
        )
        _finalize_editor(
            editor, self.nullable, self.read_only, self.description or ""
        )
        return editor

    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        value = getattr(record, self.name)  # type: ignore[assignment]
        if value is None:
            return self.expand_value(None)  # type: ignore[no-untyped-call]

        if self.formatter is None:
            self.formatter = MomentFormat.from_string(
                self.format
            )  # type: ignore[assignment]

        display = self.formatter.moment_to_string(value)
        return self.expand_value(  # type: ignore[no-untyped-call]
            value=value,
            DisplayRole=display,
            EditRole=value,
            ToolTipRole=str(value),
        )


@define
class QtDurationField(DurationField, QtField[DBM]):
    def is_editable(self) -> bool:
        """Return whether the field can be edited inline.

        Returns:
            False because duration values are not editable inline.
        """
        return False

    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        return self.not_implemented_values(record)


@define
class QtEnumField(EnumField, QtField[DBM]):
    def create_editor(self, parent) -> Optional[DrfEnumEditor]:
        """Create an editor widget for inline editing."""
        editor = DrfEnumEditor(
            ctx=self.ctx,
            parent=parent,
            name=self.name,
            description="",
            nullable=False,
            choices=self.enum_values,
        )
        _finalize_editor(
            editor, self.nullable, self.read_only, self.description or ""
        )
        return editor

    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        value = getattr(record, self.name)
        if value is None:
            return self.expand_value(None)

        if hasattr(value, "name"):
            # If the value is an Enum, we need to get its name
            value = value.name
        for k, v in self.enum_values:
            if k == value:
                return self.expand_value(
                    value=value,
                    DisplayRole=v,
                )

        logger.error(
            "EnumField %s got value %s that was not found in enum_values: %s",
            self.name,
            value,
            self.enum_values,
        )
        return self.expand_value(None)  # type: ignore[no-untyped-call]


@define
class QtFloatField(FloatField, QtField[DBM]):
    def create_editor(self, parent) -> Optional[DrfRealEditor]:
        """Create an editor widget for inline editing."""
        min_value = self.min * self.scale if self.min is not None else None
        max_value = self.max * self.scale if self.max is not None else None
        editor = DrfRealEditor(
            ctx=self.ctx,
            parent=parent,
            name=self.name,
            description="",
            nullable=False,
            decimals=self.precision,
            minimum=min_value,
            maximum=max_value,
            suffix=f" {self.unit_symbol}" if self.unit_symbol else None,
        )
        _finalize_editor(
            editor, self.nullable, self.read_only, self.description or ""
        )
        return editor

    def set_editor_data(self, editor, value: Any) -> None:
        """Populate the editor with the current value."""
        if value is not None:
            value = value * self.scale
        super().set_editor_data(editor, value)

    def editor_value(self, editor) -> Any:
        """Extract the value from the editor."""
        value = super().editor_value(editor)
        if value is NO_EDITOR_VALUE or value is None:
            return value
        if not self.scale:
            return value
        return value / self.scale

    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        value = getattr(record, self.name)  # type: ignore[assignment]
        if value is None:
            return self.expand_value(None)  # type: ignore[no-untyped-call]

        display = f"{(value * self.scale):.{self.precision}f}"
        if self.unit_symbol:
            display = f"{display} {self.unit_symbol}"

        tip = f"{(value * self.scale):.{self.precision}f}"
        if self.unit:
            tip = f"{tip} {self.unit}"

        color = Qt.GlobalColor.black

        if self.min:
            tip = f"{(self.min * self.scale):.{self.precision}f} <= {tip}"
            if value < self.min:
                color = Qt.GlobalColor.red
        if self.max:
            tip = f"{tip} <= {(self.max * self.scale):.{self.precision}f}"
            if value > self.max:
                color = Qt.GlobalColor.red

        return self.expand_value(
            value=value,
            DisplayRole=display,
            ToolTipRole=tip,
            StatusTipRole=tip,
            EditRole=value,
            ForegroundRole=QBrush(color),
            TextAlignmentRole=(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            ),
        )


@define
class QtIntegerField(IntField, QtField[DBM]):
    def create_editor(self, parent) -> Optional[DrfIntEditor]:
        """Create an editor widget for inline editing."""
        editor = DrfIntEditor(
            ctx=self.ctx,
            parent=parent,
            name=self.name,
            description="",
            nullable=False,
            minimum=self.min,
            maximum=self.max,
            suffix=f" {self.unit_symbol}" if self.unit_symbol else None,
        )
        _finalize_editor(
            editor, self.nullable, self.read_only, self.description or ""
        )
        return editor

    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        value = getattr(record, self.name)  # type: ignore[assignment]
        if value is None:
            return self.expand_value(None)  # type: ignore[no-untyped-call]

        display = f"{value:,}"
        if self.unit_symbol:
            display = f"{display} {self.unit_symbol}"

        tip = f"{value:,}"
        if self.unit:
            tip = f"{tip} {self.unit}"

        color = Qt.GlobalColor.black

        if self.min:
            tip = f"{self.min} <= {tip}"
            if value < self.min:
                color = Qt.GlobalColor.red

        if self.max:
            tip = f"{tip} <= {self.max}"
            if value > self.max:
                color = Qt.GlobalColor.red

        return self.expand_value(
            value=value,
            DisplayRole=display,
            ToolTipRole=tip,
            StatusTipRole=tip,
            EditRole=value,
            ForegroundRole=QBrush(color),
            TextAlignmentRole=(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            ),
        )


def value_for_text(self, record):
    value = getattr(record, self.name)  # type: ignore[assignment]
    if value is None:
        return self.expand_value(None)  # type: ignore[no-untyped-call]

    display = str(value).replace("\n", "\\n")
    if len(display) > 50:
        display = f"{display[:50]}..."

    tip = value
    if self.max_length:
        label = self.t("cmn.max_length", "Maximum length")
        tip = f"{label} = {self.max_length}\n{tip}"

    if self.min_length:
        label = self.t("cmn.min_length", "Minimum length")
        tip = f"{label} = {self.min_length}\n{tip}"

    return self.expand_value(
        value=value,
        DisplayRole=display,
        EditRole=value,
        ToolTipRole=value,
        StatusTipRole=value,
        TextAlignmentRole=(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        ),
        FontRole=italic_font if self.multiline else regular_font,
    )


@define
class QtStringField(StrField, QtField[DBM]):
    def create_editor(self, parent) -> Optional[QWidget]:
        """Create an editor widget for inline editing."""
        if self.multiline:
            editor = _PlainTextButtonEditor(parent)
            editor.setEnabled(not self.read_only)
        else:
            editor = DrfLineEditor(
                ctx=self.ctx,
                parent=parent,
                name=self.name,
                description="",
                nullable=False,
                min_len=self.min_length,
                max_len=self.max_length,
            )
        if not self.multiline and self.enum_values:
            editor.set_choices(self.enum_values)  # type: ignore[attr-defined]
        if not self.multiline:
            _finalize_editor(
                editor, self.nullable, self.read_only, self.description or ""
            )
        return editor

    def set_editor_data(self, editor, value: Any) -> None:
        """Populate the editor with the current value."""
        if self.multiline and isinstance(editor, _PlainTextButtonEditor):
            editor.setTextValue("" if value is None else str(value))
            return
        super().set_editor_data(editor, value)

    def configure_editor(self, editor, commit_cb) -> None:
        """Attach signals to the editor for inline editing."""
        if self.multiline and isinstance(editor, _PlainTextButtonEditor):
            editor.editingFinished.connect(lambda: commit_cb(editor))

    def editor_value(self, editor) -> Any:
        """Extract the value from the editor."""
        if self.multiline and isinstance(editor, _PlainTextButtonEditor):
            text = editor.textValue()
            if text == "" and self.nullable:
                return None
            return text
        return super().editor_value(editor)

    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        return value_for_text(self, record)


@define
class QtStringListField(StrListField, QtField[DBM]):
    def create_editor(self, parent) -> Optional[DrfTextEditor]:
        """Create an editor widget for inline editing."""
        editor = DrfTextEditor(
            ctx=self.ctx,
            parent=parent,
            name=self.name,
            description=self.description or "",
            nullable=False,
        )
        _finalize_editor(editor, self.nullable, self.read_only)
        return editor

    def set_editor_data(self, editor, value: Any) -> None:
        """Populate the editor with the current value."""
        if isinstance(value, (list, tuple)):
            text = "\n".join(str(v) for v in value)
        elif value is None:
            text = ""
        else:
            text = str(value)
        super().set_editor_data(editor, text)

    def editor_value(self, editor) -> Any:
        """Extract the value from the editor."""
        if hasattr(editor, "toPlainText"):
            raw = editor.toPlainText()  # type: ignore[attr-defined]
        else:
            raw = super().editor_value(editor)
            if raw is NO_EDITOR_VALUE:
                return raw
        parts = [
            part.strip()
            for part in str(raw).replace("\n", ",").split(",")
            if part.strip()
        ]
        if not parts:
            return None if self.nullable else []
        return parts

    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        value = getattr(record, self.name)  # type: ignore[assignment]
        if value is None:
            return self.expand_value(None)  # type: ignore[no-untyped-call]

        if len(value) == 0:
            display = "[]"
            tip = self.t("cmn.empty_list", "Empty list")
        else:
            display = f"[ {', '.join(value)} ]"
            tip = "\n".join(value)

        if len(display) > 50:
            display = f"{display[:50]}..."
        return self.expand_value(
            value=value,
            DisplayRole=display,
            EditRole=value,
            ToolTipRole=tip,
            StatusTipRole=tip,
        )


@define
class QtIntListField(IntListField, QtField[DBM]):
    def create_editor(self, parent) -> Optional[DrfTextEditor]:
        """Create an editor widget for inline editing."""
        editor = DrfTextEditor(
            ctx=self.ctx,
            parent=parent,
            name=self.name,
            description=self.description or "",
            nullable=False,
        )
        _finalize_editor(editor, self.nullable, self.read_only)
        return editor

    def set_editor_data(self, editor, value: Any) -> None:
        """Populate the editor with the current value."""
        if isinstance(value, (list, tuple)):
            text = "\n".join(str(v) for v in value)
        elif value is None:
            text = ""
        else:
            text = str(value)
        super().set_editor_data(editor, text)

    def editor_value(self, editor) -> Any:
        """Extract the value from the editor."""
        if hasattr(editor, "toPlainText"):
            raw = editor.toPlainText()  # type: ignore[attr-defined]
        else:
            raw = super().editor_value(editor)
            if raw is NO_EDITOR_VALUE:
                return raw
        parts = [
            part.strip()
            for part in str(raw).replace("\n", ",").split(",")
            if part.strip()
        ]
        if not parts:
            return None if self.nullable else []
        try:
            return [int(part) for part in parts]
        except ValueError:
            return NO_EDITOR_VALUE

    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        value = getattr(record, self.name)
        if value is None:
            return self.expand_value(None)

        if len(value) == 0:
            display = "[]"
            tip = self.t("cmn.empty_list", "Empty list")
        else:

            display = ", ".join([f"{v:,}" for v in value])
            tip = "\n".join([f"{v:,}{self.unit_symbol or ''}" for v in value])
        if len(display) > 50:
            display = f"{display[:50]}..."
        return self.expand_value(
            value=value,
            DisplayRole=display,
            EditRole=value,
            ToolTipRole=tip,
            StatusTipRole=tip,
        )


@define
class QtFloatListField(FloatListField, QtField[DBM]):
    def is_editable(self) -> bool:
        """Return whether the field can be edited inline.

        Returns:
            False because float list values are not editable inline.
        """
        return False

    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        return self.not_implemented_values(record)


@define
class QtFormattedField(FormattedField, QtField[DBM]):
    def create_editor(self, parent) -> Optional[DrfLineEditor]:
        """Create an editor widget for inline editing."""
        editor = DrfLineEditor(
            ctx=self.ctx,
            parent=parent,
            name=self.name,
            description="",
            nullable=False,
        )
        _finalize_editor(
            editor, self.nullable, self.read_only, self.description or ""
        )
        return editor

    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        return value_for_text(self, record)


class _PlainTextDialog(QDialog):
    """Dialog that edits text in a plain text editor."""

    def __init__(self, parent: QWidget, text: str) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit text")
        self._editor = QPlainTextEdit(self)
        self._editor.setPlainText(text)
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self
        )
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(self._editor, 1)
        layout.addWidget(self._buttons)
        self.setLayout(layout)

    def text(self) -> str:
        """Return the editor text."""
        return self._editor.toPlainText()


class _PlainTextButtonEditor(QToolButton):
    """Editor that opens a dialog with a plain text editor."""

    editingFinished = pyqtSignal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._text = ""
        self.setText("...")
        self.clicked.connect(self._open_dialog)

    def setTextValue(self, text: str) -> None:
        """Set the text represented by this editor."""
        self._text = text
        preview = text.replace("\n", " ").strip()
        if len(preview) > 80:
            preview = f"{preview[:80]}..."
        self.setToolTip(preview)

    def textValue(self) -> str:
        """Return the current text value."""
        return self._text

    def _open_dialog(self) -> None:
        dlg = _PlainTextDialog(self, self._text)
        dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        if dlg.exec_() == QDialog.Accepted:
            self.setTextValue(dlg.text())
            self.editingFinished.emit()


class _OpaqueCellEditor(QWidget):
    """Wrapper widget that paints an opaque background."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAutoFillBackground(True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)


class RefFilterByPart:
    def apply_sub_filter(
        self, item: "FieldFilter", selector: "Selector", path: List[str]
    ) -> Any:
        """Apply a sub-filter to this field."""
        from sqlalchemy.sql.operators import regexp_match_op

        from exdrf_qt.models.fi_op import filter_op_registry

        if len(path) == 0:
            raise ValueError("Path is empty")

        # Resolve the base relationship for this reference field.
        base_mapper = class_mapper(
            self.resource.db_model  # type: ignore[attr-defined]
        )
        base_property = base_mapper.get_property(
            self.name  # type: ignore[attr-defined]
        )
        related_entity = getattr(
            self.resource.db_model, self.name  # type: ignore[attr-defined]
        )

        # Build the chain of relationships to reach the target column.
        relationship_chain = [(related_entity, base_property.uselist)]
        current_model = base_property.mapper.class_

        # Traverse nested relationships before the final column.
        for part in path[:-1]:
            rel_property = class_mapper(current_model).get_property(part)
            if not hasattr(rel_property, "mapper"):
                raise ValueError(
                    f"Path part {part} is not a relationship property."
                )
            relationship_chain.append(
                (getattr(current_model, part), rel_property.uselist)
            )
            current_model = rel_property.mapper.class_

        # Resolve the target column on the final related model.
        column = getattr(current_model, path[-1])

        # SQLite doesn't support the flags parameter for regexp_match_op.
        # Instead, we need to embed the flags inline in the pattern using
        # Python's inline flag syntax: (?im) for case-insensitive and
        # multi-line matching.
        if (
            selector.dialect == "sqlite"
            and item.op == "regex"
            and isinstance(item.vl, str)
        ):
            # Prepend inline flags to the pattern for SQLite.
            pattern = f"(?im){item.vl}".replace("(?im)(?im)", "(?im)")
            predicate_result = regexp_match_op(column, pattern, flags=None)
        else:
            predicate = filter_op_registry[item.op].predicate
            predicate_result = predicate(column, item.vl)

        # Wrap the predicate through the relationship chain.
        for rel_attr, rel_uselist in reversed(relationship_chain):
            if rel_uselist:
                predicate_result = rel_attr.any(predicate_result)
            else:
                predicate_result = rel_attr.has(predicate_result)

        return predicate_result


@define
class QtRefManyToOneField(RefManyToOneField, RefFilterByPart, QtField[DBM]):
    def is_editable(self) -> bool:
        """Return whether the field can be edited inline."""
        if not super().is_editable():
            return False
        return getattr(self, "selector_one_class", None) is not None

    def create_editor(self, parent) -> Optional[DrfSelOneEditor]:
        """Create an editor widget for inline editing."""
        selector_cls = getattr(self, "selector_one_class", None)
        if selector_cls is None:
            return None
        editor = selector_cls(
            ctx=self.ctx,
            parent=parent,
            name=self.name,
            description=self.description or "",
            nullable=False,
        )
        _finalize_editor(editor, self.nullable, self.read_only)
        return editor

    def configure_editor(self, editor, commit_cb) -> None:
        """Attach signals to the editor for inline editing."""
        if hasattr(editor, "controlChanged"):

            def _on_change() -> None:
                if hasattr(editor, "validate_control"):
                    result = editor.validate_control()
                    if hasattr(result, "is_valid") and not result.is_valid:
                        return
                commit_cb(editor)

            editor.controlChanged.connect(_on_change)

    def set_editor_data(self, editor, value: Any) -> None:
        """Populate the editor with a safe identity value."""
        if hasattr(value, "metadata"):
            identity = _identity_value(value)
            if identity is not None:
                value = identity
        super().set_editor_data(editor, value)

    def apply_edit_value(self, db_item: DBM, value: Any, session: Any) -> None:
        """Apply the edited value to the database item."""
        mapper = cast(Any, inspect(db_item.__class__))
        rel = mapper.relationships[self.name]
        related_cls = rel.mapper.class_
        record = _resolve_ref_item(session, related_cls, value)
        setattr(db_item, self.name, record)

    def apply_sorting(self, ascending: bool) -> Any:
        """Compute sorting using the underlying foreign key column."""
        if self.fk_from is None:
            logger.log(
                1,
                "No fk_from for %s.%s; skipping sorting.",
                self.resource.name,
                self.name,
            )
            return None
        column = getattr(self.resource.db_model, self.fk_from.name)
        return column.asc() if ascending else column.desc()

    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        item = getattr(record, self.name)
        if item is None:
            return self.expand_value(None)
        label = self.part_label(item)
        return self.expand_value(
            value=label,
            EditRole=item,
        )

    def part_label(self, record: Any) -> str:
        """Compute the label for one of the components of the field."""
        raise NotImplementedError(
            "part_label is not implemented for QtRefOneToManyField"
        )


@define
class QtRefOneToManyField(RefOneToManyField, RefFilterByPart, QtField[DBM]):
    show_n_labels: int = field(default=4)

    def is_editable(self) -> bool:
        """Return whether the field can be edited inline."""
        if not super().is_editable():
            return False
        return getattr(self, "selector_multi_class", None) is not None

    def create_editor(self, parent) -> Optional[DrfSelMultiEditor]:
        """Create an editor widget for inline editing."""
        selector_cls = getattr(self, "selector_multi_class", None)
        if selector_cls is None:
            return None
        editor = selector_cls(
            ctx=self.ctx,
            parent=parent,
            name=self.name,
            description=self.description or "",
            nullable=False,
        )
        _finalize_editor(editor, self.nullable, self.read_only)
        return editor

    def configure_editor(self, editor, commit_cb) -> None:
        """Attach signals to the editor for inline editing."""
        if hasattr(editor, "controlChanged"):

            def _on_change() -> None:
                if hasattr(editor, "validate_control"):
                    result = editor.validate_control()
                    if hasattr(result, "is_valid") and not result.is_valid:
                        return
                commit_cb(editor)

            editor.controlChanged.connect(_on_change)

    def set_editor_data(self, editor, value: Any) -> None:
        """Populate the editor with a safe identity list."""
        if value is None:
            super().set_editor_data(editor, value)
            return
        if isinstance(value, (list, tuple)):
            result = []
            for item in value:
                if hasattr(item, "metadata"):
                    identity = _identity_value(item)
                    if identity is None:
                        continue
                    result.append(identity)
                else:
                    result.append(item)
            value = result
        super().set_editor_data(editor, value)

    def apply_edit_value(self, db_item: DBM, value: Any, session: Any) -> None:
        """Apply the edited value to the database item."""
        mapper = cast(Any, inspect(db_item.__class__))
        rel = mapper.relationships[self.name]
        related_cls = rel.mapper.class_
        records = _resolve_ref_list(session, related_cls, value)
        collection_cls = rel.collection_class or list
        setattr(db_item, self.name, collection_cls(records))

    def apply_sorting(self, ascending: bool) -> Any:
        """Skip sorting for collection relationships."""
        logger.log(
            1,
            "Skipping sorting for collection field %s.%s",
            self.resource.name,
            self.name,
        )
        return None

    def values(self, record: DBM) -> Dict[Qt.ItemDataRole, Any]:
        """Compute the values for each role for this field.

        As this is a field that has multiple values, we ask the implementation
        to provide to helper methods to compute the ID and label for each
        of the items.

        The resulted edit role will have the list of IDs and the display role
        will have a comma-separated list of the labels. If the list is
        longer than `show_n_labels`, the last label will be "...",
        with the full list shown in the tooltip.
        """
        items = getattr(record, self.name)
        if items is None:
            return self.expand_value(None)

        labels = []
        ids = []
        for item in items:
            labels.append(self.part_label(item))
            ids.append(self.part_id(item))

        display_labels = (
            labels
            if len(labels) <= self.show_n_labels
            else (labels[: self.show_n_labels] + ["..."])
        )
        tooltip = "\n".join(labels)
        display = ", ".join(display_labels)

        return self.expand_value(
            value=display,
            EditRole=ids,
            ToolTipRole=tooltip,
        )

    def part_id(self, record: Any) -> RecIdType:
        """Compute the ID for one of the components of the field."""
        raise NotImplementedError(
            "part_id is not implemented for QtRefOneToManyField"
        )

    def part_label(self, record: Any) -> str:
        """Compute the label for one of the components of the field."""
        raise NotImplementedError(
            "part_label is not implemented for QtRefOneToManyField"
        )


@define
class QtRefOneToOneField(RefOneToOneField, RefFilterByPart, QtField[DBM]):
    def is_editable(self) -> bool:
        """Return whether the field can be edited inline."""
        if not super().is_editable():
            return False
        return getattr(self, "selector_one_class", None) is not None

    def create_editor(self, parent) -> Optional[DrfSelOneEditor]:
        """Create an editor widget for inline editing."""
        selector_cls = getattr(self, "selector_one_class", None)
        if selector_cls is None:
            return None
        editor = selector_cls(
            ctx=self.ctx,
            parent=parent,
            name=self.name,
            description=self.description or "",
            nullable=False,
        )
        _finalize_editor(editor, self.nullable, self.read_only)
        return editor

    def configure_editor(self, editor, commit_cb) -> None:
        """Attach signals to the editor for inline editing."""
        if hasattr(editor, "controlChanged"):

            def _on_change() -> None:
                if hasattr(editor, "validate_control"):
                    result = editor.validate_control()
                    if hasattr(result, "is_valid") and not result.is_valid:
                        return
                commit_cb(editor)

            editor.controlChanged.connect(_on_change)

    def set_editor_data(self, editor, value: Any) -> None:
        """Populate the editor with a safe identity value."""
        if hasattr(value, "metadata"):
            identity = _identity_value(value)
            if identity is not None:
                value = identity
        super().set_editor_data(editor, value)

    def apply_edit_value(self, db_item: DBM, value: Any, session: Any) -> None:
        """Apply the edited value to the database item."""
        mapper = cast(Any, inspect(db_item.__class__))
        rel = mapper.relationships[self.name]
        related_cls = rel.mapper.class_
        record = _resolve_ref_item(session, related_cls, value)
        setattr(db_item, self.name, record)

    def apply_sorting(self, ascending: bool) -> Any:
        """Compute sorting using the underlying foreign key column."""
        if self.fk_from is None:
            logger.log(
                1,
                "No fk_from for %s.%s; skipping sorting.",
                self.resource.name,
                self.name,
            )
            return None
        column = getattr(self.resource.db_model, self.fk_from.name)
        return column.asc() if ascending else column.desc()

    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        item = getattr(record, self.name)
        if item is None:
            return self.expand_value(None)
        label = self.part_label(item)
        return self.expand_value(
            value=label,
            EditRole=item,
        )

    def part_label(self, record: Any) -> str:
        """Compute the label for one of the components of the field."""
        raise NotImplementedError(
            "part_label is not implemented for QtRefOneToManyField"
        )


@define
class QtRefManyToManyField(RefManyToManyField, RefFilterByPart, QtField[DBM]):
    show_n_labels: int = field(default=4)

    def is_editable(self) -> bool:
        """Return whether the field can be edited inline."""
        if not super().is_editable():
            return False
        return getattr(self, "selector_multi_class", None) is not None

    def create_editor(self, parent) -> Optional[DrfSelMultiEditor]:
        """Create an editor widget for inline editing."""
        selector_cls = getattr(self, "selector_multi_class", None)
        if selector_cls is None:
            return None
        editor = selector_cls(
            ctx=self.ctx,
            parent=parent,
            name=self.name,
            description=self.description or "",
            nullable=False,
        )
        _finalize_editor(editor, self.nullable, self.read_only)
        return editor

    def configure_editor(self, editor, commit_cb) -> None:
        """Attach signals to the editor for inline editing."""
        if hasattr(editor, "controlChanged"):

            def _on_change() -> None:
                if hasattr(editor, "validate_control"):
                    result = editor.validate_control()
                    if hasattr(result, "is_valid") and not result.is_valid:
                        return
                commit_cb(editor)

            editor.controlChanged.connect(_on_change)

    def set_editor_data(self, editor, value: Any) -> None:
        """Populate the editor with a safe identity list."""
        if value is None:
            super().set_editor_data(editor, value)
            return
        if isinstance(value, (list, tuple)):
            result = []
            for item in value:
                if hasattr(item, "metadata"):
                    identity = _identity_value(item)
                    if identity is None:
                        continue
                    result.append(identity)
                else:
                    result.append(item)
            value = result
        super().set_editor_data(editor, value)

    def apply_edit_value(self, db_item: DBM, value: Any, session: Any) -> None:
        """Apply the edited value to the database item."""
        mapper = cast(Any, inspect(db_item.__class__))
        rel = mapper.relationships[self.name]
        related_cls = rel.mapper.class_
        records = _resolve_ref_list(session, related_cls, value)
        collection_cls = rel.collection_class or list
        setattr(db_item, self.name, collection_cls(records))

    def apply_sorting(self, ascending: bool) -> Any:
        """Skip sorting for collection relationships."""
        logger.log(
            1,
            "Skipping sorting for collection field %s.%s",
            self.resource.name,
            self.name,
        )
        return None

    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        items = getattr(record, self.name)
        if items is None:
            return self.expand_value(None)

        labels = []
        ids = []
        for item in items:
            labels.append(self.part_label(item))
            ids.append(self.part_id(item))

        display_labels = (
            labels
            if len(labels) <= self.show_n_labels
            else (labels[: self.show_n_labels] + ["..."])
        )
        tooltip = "\n".join(labels)
        display = ", ".join(display_labels)

        return self.expand_value(
            value=display,
            EditRole=ids,
            ToolTipRole=tooltip,
        )

    def part_id(self, record: Any) -> RecIdType:
        """Compute the ID for one of the components of the field."""
        raise NotImplementedError(
            "part_id is not implemented for QtRefOneToManyField"
        )

    def part_label(self, record: Any) -> str:
        """Compute the label for one of the components of the field."""
        raise NotImplementedError(
            "part_label is not implemented for QtRefOneToManyField"
        )


@define
class QtFilterField(FilterField, QtField[DBM]):
    def is_editable(self) -> bool:
        """Return whether the field can be edited inline.

        Returns:
            False because filter fields are not editable inline.
        """
        return False

    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        return self.not_implemented_values(record)


@define
class QtSortField(SortField, QtField[DBM]):
    def is_editable(self) -> bool:
        """Return whether the field can be edited inline.

        Returns:
            False because sort fields are not editable inline.
        """
        return False

    def values(self, record) -> Dict[Qt.ItemDataRole, Any]:
        return self.not_implemented_values(record)
