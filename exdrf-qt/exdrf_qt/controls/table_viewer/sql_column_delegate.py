"""Item delegate for table viewer that creates type-aware editors from
introspection.

SqlColumnDelegate creates editors per column based on SQLAlchemy column
types (Boolean -> QCheckBox, Integer -> QLineEdit + QIntValidator, etc.)
and respects a per-column editability check (plugin point). For nullable
columns, a Clear button (broom icon) is shown to set the value to NULL.
"""

import logging
from datetime import date, datetime
from typing import Any, Callable, Optional, cast

from PyQt5.QtCore import QModelIndex, QSortFilterProxyModel, Qt
from PyQt5.QtGui import (
    QColor,
    QDoubleValidator,
    QIntValidator,
    QPainter,
    QPalette,
)
from PyQt5.QtWidgets import (
    QAction,
    QCheckBox,
    QDateEdit,
    QDateTimeEdit,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QWidget,
)

logger = logging.getLogger(__name__)
VERBOSE = 1

# Property name set on the wrapper when user clicks Clear to store NULL.
_CLEAR_TO_NULL_PROP = "_clear_to_null"
# Attribute on wrapper holding the inner editor widget.
_INNER_EDITOR_ATTR = "_inner_editor"

# Text and style for displaying null values in the table.
_NULL_DISPLAY_TEXT = "NULL"


def _is_null_display(value: Any) -> bool:
    """Return True if the cell value should be shown as NULL.

    Args:
        value: Model data (DisplayRole or EditRole).

    Returns:
        True if value is None or empty/whitespace string.
    """
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def _paint_null_cell(
    delegate: QStyledItemDelegate,
    painter: QPainter,
    option: QStyleOptionViewItem,
    index: QModelIndex,
    text: str = _NULL_DISPLAY_TEXT,
) -> None:
    """Draw NULL placeholder: background/selection via style, then italic
    grey centered text.

    Args:
        delegate: Delegate instance (for initStyleOption).
        painter: Painter to use.
        option: Style option providing the cell rect and state.
        index: Model index (for initStyleOption).
        text: Text to draw (default "NULL").
    """
    delegate.initStyleOption(option, index)
    option.text = text
    option.displayAlignment = Qt.AlignmentFlag.AlignCenter
    pal = option.palette
    pal.setColor(
        QPalette.ColorGroup.Normal,
        QPalette.ColorRole.Text,
        QColor(128, 128, 128),
    )
    option.palette = pal
    font = option.font
    font.setItalic(True)
    option.font = font
    style = option.widget.style() if option.widget else None
    if style is not None:
        style.drawControl(
            QStyle.ControlElement.CE_ItemViewItem,
            option,
            painter,
            option.widget,
        )
    else:
        painter.save()
        painter.setFont(option.font)
        painter.setPen(QColor(128, 128, 128))
        painter.drawText(
            option.rect,
            int(Qt.AlignmentFlag.AlignCenter) | int(Qt.TextFlag.TextSingleLine),
            text,
        )
        painter.restore()


class TableCellDelegate(QStyledItemDelegate):
    """Default table cell delegate that paints NULL values as italic grey
    centered text.
    """

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        """Paint the cell; show NULL for null/empty values.

        Args:
            painter: Painter to use.
            option: Style option for the cell.
            index: Model index.
        """
        if index.isValid():
            model = index.model()
            if model is not None:
                value = model.data(index, Qt.ItemDataRole.DisplayRole)
                if _is_null_display(value):
                    _paint_null_cell(self, painter, option, index)
                    return
        super().paint(painter, option, index)


class SqlColumnDelegate(QStyledItemDelegate):
    """Delegate that creates type-aware editors for SQL table columns.

    Uses the source model's reflected column types to choose the editor.
    Only creates an editor if is_column_editable(column_name) returns True.
    For nullable columns, wraps the editor with a Clear button to set NULL.
    Works with a proxy model: maps proxy indices to source for model calls.

    Attributes:
        is_column_editable: Callable (column_name: str) -> bool; when the
            list of checks is empty the viewer treats all columns as
            editable; otherwise a column is editable if any check
            returns True.
        get_icon: Optional callable (icon_name: str) -> QIcon for the
            Clear button; if None, no icon is set.
        get_text: Optional callable (key: str, fallback: str) -> str for
            the Clear button label; if None, "Clear" is used.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        is_column_editable: Optional[Callable[[str], bool]] = None,
        get_icon: Optional[Callable[[str], Any]] = None,
        get_text: Optional[Callable[[str, str], str]] = None,
    ) -> None:
        """Initialize the delegate.

        Args:
            parent: Optional parent widget.
            is_column_editable: Optional callable to decide if a column
                is editable; if None, all columns are considered editable.
            get_icon: Optional callable to resolve icon by name (e.g. for
                Clear button); used with "clear_to_null" or "broom".
            get_text: Optional callable (key, default) for translated
                Clear label.
        """
        super().__init__(parent)
        self.is_column_editable = is_column_editable or (lambda _: True)
        self.get_icon = get_icon
        self.get_text = get_text or (lambda _k, d: d)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        """Paint the cell; show NULL for null/empty values.

        Args:
            painter: Painter to use.
            option: Style option for the cell.
            index: Model index (proxy space).
        """
        if index.isValid():
            model = index.model()
            if model is not None:
                value = model.data(index, Qt.ItemDataRole.DisplayRole)
                if _is_null_display(value):
                    _paint_null_cell(self, painter, option, index)
                    return
        super().paint(painter, option, index)

    def createEditor(
        self,
        parent: QWidget,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> Optional[QWidget]:
        """Create a type-appropriate editor for the cell if the column is
        editable. For nullable columns, wraps the editor with a Clear
        button to set the value to NULL.

        Args:
            parent: Parent widget for the editor.
            option: Style option for the cell.
            index: Model index (in proxy space).

        Returns:
            Editor widget or None if the column is not editable or type
            is unknown.
        """
        model = index.model()
        if model is None:
            return None
        proxy = cast(QSortFilterProxyModel, model)
        source_index = proxy.mapToSource(index)
        source_model = proxy.sourceModel()
        if source_model is None:
            return None
        col = source_index.column()
        headers = source_model.raw_headers()
        if col < 0 or col >= len(headers):
            return None
        column_name = headers[col]
        if not self.is_column_editable(column_name):
            return None

        col_type = source_model.raw_column_type(col)
        type_name = type(col_type).__name__ if col_type else ""
        nullable = source_model.raw_column_nullable(col)

        inner: Optional[QWidget] = None
        if type_name == "Boolean":
            cb = QCheckBox(parent)
            if nullable:
                cb.setTristate(True)
            inner = cb
        elif type_name in ("Integer", "SmallInteger", "BigInteger"):
            edit = QLineEdit(parent)
            edit.setValidator(QIntValidator(edit))
            inner = edit
        elif type_name in ("Float", "Numeric", "DECIMAL"):
            edit = QLineEdit(parent)
            edit.setValidator(QDoubleValidator(edit))
            inner = edit
        elif type_name == "Date":
            de = QDateEdit(parent)
            de.setCalendarPopup(True)
            inner = de
        elif type_name in ("DateTime", "TIMESTAMP"):
            dte = QDateTimeEdit(parent)
            dte.setCalendarPopup(True)
            inner = dte
        else:
            inner = QLineEdit(parent)

        if inner is None:
            return None
        if not nullable:
            return inner

        # Add Clear as a trailing action on QLineEdit when possible; nullable
        # Boolean uses tristate checkbox (no wrapper); wrap only date/datetime.
        if isinstance(inner, QLineEdit):
            self._add_clear_action_to_line_edit(inner)
            return inner
        if isinstance(inner, QCheckBox):
            return inner
        # QDateEdit, QDateTimeEdit: wrap with a Clear button.
        container = QWidget(parent)
        lay = QHBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(inner, 1)
        clear_btn = QPushButton(container)
        clear_btn.setToolTip(self.get_text("table_viewer.clear", "Clear"))
        try:
            if self.get_icon:
                clear_btn.setIcon(self.get_icon("clear_to_null"))
        except Exception as e:
            logger.log(
                VERBOSE,
                "SqlColumnDelegate: get_icon clear_to_null: %s",
                e,
                exc_info=True,
            )
        clear_btn.setText(self.get_text("table_viewer.clear", "Clear"))
        lay.addWidget(clear_btn)
        setattr(container, _INNER_EDITOR_ATTR, inner)
        clear_btn.clicked.connect(lambda: self._on_clear_clicked(container))
        return container

    def _add_clear_action_to_line_edit(self, line_edit: QLineEdit) -> None:
        """Add a trailing Clear action to the line edit to set value to NULL.

        Args:
            line_edit: The QLineEdit to add the action to.
        """
        ac = QAction(line_edit)
        ac.setToolTip(self.get_text("table_viewer.clear", "Clear"))
        try:
            if self.get_icon:
                ac.setIcon(self.get_icon("clear_to_null"))
        except Exception as e:
            logger.log(
                VERBOSE,
                "SqlColumnDelegate: get_icon clear_to_null: %s",
                e,
                exc_info=True,
            )
        ac.triggered.connect(lambda: self._on_clear_clicked(line_edit))
        line_edit.addAction(ac, QLineEdit.ActionPosition.LeadingPosition)

    def _on_clear_clicked(self, editor: QWidget) -> None:
        """Mark the editor as cleared to NULL, commit, and close.

        Emit commitData so the view calls setModelData; then closeEditor.

        Args:
            editor: The editor widget (line edit, spinbox, or wrapper).
        """
        editor.setProperty(_CLEAR_TO_NULL_PROP, True)
        self.commitData.emit(editor)  # type: ignore[arg-type]
        self.closeEditor.emit(editor)  # type: ignore[arg-type]

    def _inner_editor(self, editor: QWidget) -> QWidget:
        """Return the inner editor if editor is a Clear wrapper, else editor."""
        return cast(QWidget, getattr(editor, _INNER_EDITOR_ATTR, editor))

    def setEditorData(
        self, editor: Optional[QWidget], index: QModelIndex
    ) -> None:
        """Load the current model value into the editor.

        Args:
            editor: Editor widget created by createEditor (may be wrapper).
            index: Model index (proxy space).
        """
        if editor is None:
            return
        ed = self._inner_editor(editor)
        model = index.model()
        if model is None:
            return
        proxy = cast(QSortFilterProxyModel, model)
        source_index = proxy.mapToSource(index)
        source_model = proxy.sourceModel()
        if source_model is None:
            return
        value = source_model.data(source_index, Qt.ItemDataRole.EditRole)
        if value is None:
            value = ""

        if isinstance(ed, QCheckBox):
            if value is None and ed.isTristate():
                ed.setCheckState(Qt.CheckState.PartiallyChecked)
            elif value:
                ed.setCheckState(Qt.CheckState.Checked)
            else:
                ed.setCheckState(Qt.CheckState.Unchecked)
            return
        if isinstance(ed, QDateEdit):
            try:
                if isinstance(value, date):
                    ed.setDate(value)  # type: ignore[arg-type]
                elif isinstance(value, datetime):
                    ed.setDate(value.date())  # type: ignore[arg-type]
                else:
                    ed.setDate(
                        datetime.strptime(
                            str(value).strip(), "%Y-%m-%d"
                        ).date()  # type: ignore[arg-type]
                    )
            except Exception as e:
                logger.log(
                    VERBOSE,
                    "SqlColumnDelegate.setEditorData date: %s",
                    e,
                    exc_info=True,
                )
            return
        if isinstance(ed, QDateTimeEdit):
            try:
                if isinstance(value, datetime):
                    ed.setDateTime(value)  # type: ignore[arg-type]
                elif isinstance(value, date):
                    ed.setDateTime(  # type: ignore[arg-type]
                        datetime.combine(value, datetime.min.time())
                    )
                else:
                    ed.setDateTime(  # type: ignore[arg-type]
                        datetime.fromisoformat(
                            str(value).strip().replace("Z", "+00:00")
                        )
                    )
            except Exception as e:
                logger.log(
                    VERBOSE,
                    "SqlColumnDelegate.setEditorData datetime: %s",
                    e,
                    exc_info=True,
                )
            return
        if isinstance(ed, QLineEdit):
            ed.setText("" if value is None else str(value))

    def setModelData(
        self,
        editor: Optional[QWidget],
        model: object,
        index: QModelIndex,
    ) -> None:
        """Write the editor value back to the source model.

        If the user clicked Clear (nullable column), writes None. For
        nullable text fields, empty string is written as NULL by the model.

        Args:
            editor: Editor widget that holds the new value (may be wrapper).
            model: The view's model (proxy).
            index: Model index in proxy space.
        """
        if editor is None:
            return
        model = index.model()
        if model is None:
            return
        proxy = cast(QSortFilterProxyModel, model)
        source_index = proxy.mapToSource(index)
        source_model = proxy.sourceModel()
        if source_model is None:
            return

        if bool(editor.property(_CLEAR_TO_NULL_PROP)):
            source_model.setData(
                source_index,
                None,
                Qt.ItemDataRole.EditRole,
            )
            return

        ed = self._inner_editor(editor)
        if isinstance(ed, QCheckBox):
            if (
                ed.isTristate()
                and ed.checkState() == Qt.CheckState.PartiallyChecked
            ):
                val = None
            else:
                val = ed.isChecked()
            source_model.setData(
                source_index,
                val,
                Qt.ItemDataRole.EditRole,
            )
            return
        if isinstance(ed, QDateEdit):
            source_model.setData(
                source_index,
                ed.date().toPyDate(),
                Qt.ItemDataRole.EditRole,
            )
            return
        if isinstance(ed, QDateTimeEdit):
            source_model.setData(
                source_index,
                ed.dateTime().toPyDateTime(),
                Qt.ItemDataRole.EditRole,
            )
            return
        if isinstance(ed, QLineEdit):
            text = ed.text()
            source_model.setData(
                source_index,
                text,
                Qt.ItemDataRole.EditRole,
            )

    def updateEditorGeometry(
        self,
        editor: QWidget,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        """Set the editor geometry to the cell rect.

        Args:
            editor: Editor widget to position.
            option: Style option whose rect is used for geometry.
            index: Model index (unused).
        """
        editor.setGeometry(option.rect)
