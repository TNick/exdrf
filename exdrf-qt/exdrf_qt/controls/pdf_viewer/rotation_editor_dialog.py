"""Dialog for editing per-page rotation angles."""

from typing import TYPE_CHECKING, Dict, List, cast

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from typing import Callable


class RotationEditorDialog(QDialog):
    """Simple dialog for editing per-page rotation angles."""

    def __init__(
        self,
        parent: QWidget,
        pages: List[int],
        rotations: Dict[int, int],
        translator: "Callable[..., str]",
    ):
        """Build the rotation editor table and populate it with defaults."""
        super().__init__(parent)
        self._pages = pages
        self._translator = translator
        self.setWindowTitle(
            translator("pdf.split.rotations.title", "Page rotations")
        )

        # Create the table that lists each page with its rotation selector.
        self._table = QTableWidget(len(pages), 2, self)
        self._table.setHorizontalHeaderLabels(
            [
                translator("pdf.split.rotations.page", "Page"),
                translator("pdf.split.rotations.rotation", "Rotation"),
            ]
        )
        header = self._table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
        v_header = self._table.verticalHeader()
        if v_header is not None:
            v_header.setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        for row, page in enumerate(pages):
            item = QTableWidgetItem(str(page))
            flags = cast(
                Qt.ItemFlags,
                Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable,
            )
            item.setFlags(flags)
            self._table.setItem(row, 0, item)
            combo = QComboBox()
            for angle in (0, 90, 180, 270):
                label = translator(
                    "pdf.split.rotations.option",
                    "{value}°",
                    value=angle,
                )
                combo.addItem(label, angle)
            current = rotations.get(page, 0) % 360
            idx = combo.findData(current)
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            self._table.setCellWidget(row, 1, combo)

        # Standard OK/Cancel button box controls dialog acceptance.
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        # Lay out the table above the button row.
        layout = QVBoxLayout()
        layout.addWidget(self._table)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def rotations(self) -> Dict[int, int]:
        """Return the rotation map encoded by the dialog."""
        values: Dict[int, int] = {}
        for row, page in enumerate(self._pages):
            widget = self._table.cellWidget(row, 1)
            if isinstance(widget, QComboBox):
                value = widget.currentData()
                if isinstance(value, int):
                    normalized = value % 360
                    if normalized % 90 != 0:
                        normalized = 0
                    if normalized:
                        values[page] = normalized
                    elif page in values:
                        del values[page]
        return values
