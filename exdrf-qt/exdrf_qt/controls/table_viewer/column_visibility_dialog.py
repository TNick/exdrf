"""Dialog to choose which table columns are visible, with a filter."""

from typing import TYPE_CHECKING, List

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext


class ColumnVisibilityDialog(QDialog, QtUseContext):
    """Dialog with checkboxes per column and a line edit to filter the list.

    Attributes:
        ctx: The application context (for translation).
        _headers: Column names in model order.
        _list: List widget with one checkable item per column.
        _filter_edit: Line edit to filter visible items by name.
    """

    ctx: "QtContext"
    _headers: List[str]
    _list: QListWidget
    _filter_edit: QLineEdit

    def __init__(
        self,
        parent: QDialog,
        ctx: "QtContext",
        headers: List[str],
        initial_visible: List[bool],
        **kwargs,
    ) -> None:
        """Build the dialog and populate the list.

        Args:
            parent: Parent widget.
            ctx: Application context.
            headers: Column names in model order (one per column index).
            initial_visible: Whether each column is visible (same length as
                headers).
            **kwargs: Passed to QDialog.
        """
        super().__init__(parent, **kwargs)
        self.ctx = ctx
        self._headers = list(headers)
        self.setup_ui()
        self._populate_list(initial_visible)

    def setup_ui(self) -> None:
        """Create filter line edit, list widget, and button box."""
        layout = QVBoxLayout(self)
        self._filter_edit = QLineEdit(self)
        self._filter_edit.setPlaceholderText(
            self.t(
                "column_visibility.filter_placeholder",
                "Filter columns…",
            )
        )
        self._filter_edit.textChanged.connect(self._on_filter_changed)
        layout.addWidget(self._filter_edit)

        self._list = QListWidget(self)
        self._list.setAlternatingRowColors(True)
        layout.addWidget(self._list)

        bbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        layout.addWidget(bbox)

        self.setWindowTitle(
            self.t(
                "column_visibility.title",
                "Choose visible columns",
            )
        )

    def _populate_list(self, initial_visible: List[bool]) -> None:
        """Add one checkable item per column; hide rows by filter afterward."""
        self._list.clear()
        for i, name in enumerate(self._headers):
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked
                if i < len(initial_visible) and initial_visible[i]
                else Qt.CheckState.Unchecked
            )
            item.setData(Qt.ItemDataRole.UserRole, i)
            self._list.addItem(item)
        self._on_filter_changed(self._filter_edit.text())

    def _on_filter_changed(self, text: str) -> None:
        """Show list items whose column name contains the filter (case-insensitive)."""
        needle = text.strip().lower()
        for row in range(self._list.count()):
            item = self._list.item(row)
            if item is None:
                continue
            label = item.text()
            item.setHidden(needle != "" and needle not in label.lower())

    def get_visibility(self) -> List[bool]:
        """Return visibility for each column index (True = visible).

        Returns:
            List of booleans, one per column, in model order.
        """
        out: List[bool] = [False] * len(self._headers)
        for row in range(self._list.count()):
            item = self._list.item(row)
            if item is None:
                continue
            idx = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(idx, int) and 0 <= idx < len(out):
                out[idx] = item.checkState() == Qt.CheckState.Checked
        return out
