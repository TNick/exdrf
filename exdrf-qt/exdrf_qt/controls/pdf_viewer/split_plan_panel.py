"""Right-hand panel that manages PDF split definitions."""

# pyright: reportMissingImports=false

import importlib
import logging
import os
import re
from functools import partial
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

from PyQt5.QtCore import QEvent, QObject, QPoint, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from exdrf_qt.controls.pdf_viewer.rotation_editor_dialog import (
    RotationEditorDialog,
)
from exdrf_qt.controls.pdf_viewer.split_entry import SplitEntry
from exdrf_qt.controls.pdf_viewer.split_preview_window import (
    SplitPreviewWindow,
)

_yaml: Any
try:
    _yaml = cast(Any, importlib.import_module("yaml"))
except Exception:  # pragma: no cover - optional dependency
    _yaml = None
yaml = cast(Any, _yaml)

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from exdrf_qt.controls.pdf_viewer.pdf_image_viewer import (
        PdfImageViewer,
    )

logger = logging.getLogger(__name__)


class SplitPlanPanel(QWidget):
    """Right-hand panel that manages PDF split definitions."""

    generateAllRequested = pyqtSignal()
    generateSelectedRequested = pyqtSignal()
    ocrModeChanged = pyqtSignal(str)
    ocrEngineChanged = pyqtSignal(str)

    def __init__(self, viewer: "PdfImageViewer"):
        """Compose the sidebar UI and initialize storage helpers."""
        super().__init__(viewer)
        self._viewer = viewer
        self._total_pages = 0
        self._source_path: Optional[str] = None
        self._ocr_mode = "auto"
        self._ocr_engine = "tesseract"
        self._paddle_available = False
        self._row_rotations: List[Dict[int, int]] = []
        self._storage_enabled = False
        self._yaml_path: Optional[str] = None
        self._loading_state = False
        self._preview_windows: List[SplitPreviewWindow] = []
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(800)
        self._save_timer.timeout.connect(self._persist_to_yaml)
        self._warned_yaml_missing = False
        self._ocr_mode_labels: Dict[str, str] = {
            "auto": self._t("pdf.ocr.mode.auto", "Auto"),
            "digits": self._t("pdf.ocr.mode.digits", "Digits only"),
            "letters": self._t("pdf.ocr.mode.letters", "Letters only"),
            "handwriting": self._t(
                "pdf.ocr.mode.handwriting",
                "Handwriting (beta)",
            ),
        }
        self._ocr_engine_labels: Dict[str, str] = {
            "paddle": self._t("pdf.ocr.engine.paddle", "PaddleOCR"),
            "tesseract": self._t("pdf.ocr.engine.tesseract", "Tesseract"),
        }

        # Provide a minimum width so the widgets remain legible.
        self.setMinimumWidth(280)

        # High-level title and metadata that summarize the active document.
        title = QLabel(self._t("pdf.split.title", "PDF Split Planner"))
        title.setStyleSheet("font-weight: bold;")

        self.lbl_source = QLabel(
            self._t("pdf.split.source_none", "Source: none")
        )
        self.lbl_pages = QLabel(self._t("pdf.split.pages_label", "Pages: 0"))

        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.addWidget(self.lbl_source)
        info_layout.addWidget(self.lbl_pages)

        # Editable table that lists all split definitions.
        self.table = QTableWidget(0, 3)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        triggers = (
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.SelectedClicked
        )
        self.table.setEditTriggers(
            cast(QAbstractItemView.EditTriggers, triggers)
        )
        self.table.setHorizontalHeaderLabels(
            [
                self._t("pdf.split.index_column", "#"),
                self._t("pdf.split.pages_column", "Pages"),
                self._t("pdf.split.title_column", "Title"),
            ]
        )
        header = self.table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.Stretch)
        vertical_header = self.table.verticalHeader()
        if vertical_header is not None:
            vertical_header.setVisible(False)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.itemChanged.connect(self._handle_item_changed)

        # Install event filter for keyboard shortcuts.
        self.table.installEventFilter(self)

        # Buttons for adding/removing rows near the table header.
        self.btn_add = QPushButton(self._t("pdf.split.add_row", "Add row"))
        self.btn_add.clicked.connect(self._handle_add_row)
        self.btn_remove = QPushButton(
            self._t("pdf.split.remove_row", "Remove selected")
        )
        self.btn_remove.clicked.connect(self.remove_selected_rows)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.addWidget(self.btn_add)
        controls.addWidget(self.btn_remove)
        controls.addStretch(1)

        # Checkbox for filename prefixes keeps output ordering predictable.
        self.chk_prefix = QCheckBox(
            self._t(
                "pdf.split.prefix",
                "Prefix filenames with index (001., 002., ...)",
            )
        )
        self.chk_prefix.setChecked(True)
        self.chk_prefix.toggled.connect(self._handle_prefix_toggled)

        # OCR capture output and split generation buttons.
        self.btn_generate_all = QPushButton(
            self._t("pdf.split.generate_all", "Create all files")
        )
        self.btn_generate_all.clicked.connect(self.generateAllRequested.emit)
        self.btn_generate_all.setEnabled(False)

        self.ocr_label = QLabel(
            self._t("pdf.ocr.result_label", "Captured OCR text")
        )
        self.ocr_text = QPlainTextEdit()
        self.ocr_text.setReadOnly(True)
        self.ocr_text.setPlaceholderText(
            self._t(
                "pdf.ocr.placeholder",
                "Use the OCR tool to capture text snippets.",
            )
        )
        self.ocr_text.setMaximumHeight(120)
        self.ocr_text.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.ocr_text.customContextMenuRequested.connect(
            self._show_ocr_text_menu
        )

        # Final assembly of the sidebar layout.
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(title)
        layout.addLayout(info_layout)
        layout.addLayout(controls)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.ocr_label)
        layout.addWidget(self.ocr_text)
        layout.addWidget(self.chk_prefix)
        layout.addWidget(self.btn_generate_all)
        self.setLayout(layout)

    def _t(self, key: str, default: str, **kwargs) -> str:
        """Helper for translations via the owning viewer."""
        return self._viewer.t(key, default, **kwargs)

    def add_row(
        self,
        pages: str,
        title: str,
        start_title_edit: bool = False,
        rotations: Optional[Dict[int, int]] = None,
    ) -> int:
        """Insert a new editable row, optionally focusing the title."""
        row = self.table.rowCount()
        self.table.insertRow(row)
        # Index column (read-only)
        index_item = QTableWidgetItem(str(row + 1))
        index_flags = cast(
            Qt.ItemFlags,
            Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable,
        )
        index_item.setFlags(index_flags)
        self.table.setItem(row, 0, index_item)
        # Pages column
        self.table.setItem(row, 1, QTableWidgetItem(pages))
        # Title column
        self.table.setItem(row, 2, QTableWidgetItem(title))
        self._ensure_rotation_store(row)
        if rotations:
            self._set_row_rotations(row, rotations)
        if start_title_edit:
            self._start_title_edit(row)
        self._update_index_column()
        self._schedule_save()
        return row

    def add_page_to_last(self, page: int, rotation: int = 0) -> bool:
        """Append the provided page number to the last entry."""
        if page <= 0:
            return False
        if self.table.rowCount() == 0:
            row = self.add_row(
                str(page),
                "",
                start_title_edit=True,
                rotations={page: rotation} if rotation else None,
            )
            self.table.selectRow(row)
            return True
        row = self.table.rowCount() - 1
        self.table.selectRow(row)
        added = self._append_page_to_row(row, page)
        if added:
            self._set_page_rotation(row, page, rotation)
            self._schedule_save()
        return added

    def add_page_to_rows(
        self,
        page: int,
        rows: Optional[List[int]] = None,
        rotation: int = 0,
    ) -> int:
        """Append the provided page number to every row in the given list."""
        if page <= 0:
            return 0
        targets = rows if rows is not None else self.selected_rows()
        updated = 0
        for row in targets:
            if self._append_page_to_row(row, page):
                updated += 1
                self._set_page_rotation(row, page, rotation)
        if updated:
            self._schedule_save()
        return updated

    def create_entry_for_page(self, page: int, rotation: int = 0) -> int:
        """Create a brand new entry that only contains the provided page."""
        rotations = {page: rotation} if rotation else None
        row = self.add_row(
            str(page),
            "",
            start_title_edit=True,
            rotations=rotations,
        )
        self.table.selectRow(row)
        return row

    def _start_title_edit(self, row: int):
        """Focus and begin editing the title cell for the provided row."""
        if row < 0 or row >= self.table.rowCount():
            return

        # Defer activation so the editor reliably opens after the row renders.
        def activate_editor(target_row: int):
            if target_row < 0 or target_row >= self.table.rowCount():
                return
            self.table.setFocus(Qt.FocusReason.OtherFocusReason)
            self.table.setCurrentCell(target_row, 2)
            item = self.table.item(target_row, 2)
            if item is None:
                item = QTableWidgetItem("")
                self.table.setItem(target_row, 2, item)
            self.table.editItem(item)

        QTimer.singleShot(0, partial(activate_editor, row))

    def _append_page_to_row(self, row: int, page: int) -> bool:
        """Append a page number to a specific row, avoiding duplicates."""
        if row < 0 or row >= self.table.rowCount():
            return False
        item = self.table.item(row, 1)
        if item is None:
            item = QTableWidgetItem("")
            self.table.setItem(row, 1, item)
        existing = item.text().strip()
        tokens = {tok for tok in re.split(r"[,\s]+", existing) if tok}
        if str(page) in tokens:
            return False
        new_value = f"{existing}, {page}" if existing else str(page)
        item.setText(new_value)
        return True

    def remove_selected_rows(self):
        """Remove currently selected definitions."""
        rows = sorted(self.selected_rows(), reverse=True)
        for row in rows:
            self.table.removeRow(row)
            if 0 <= row < len(self._row_rotations):
                self._row_rotations.pop(row)
        if rows:
            self._update_index_column()
            self._schedule_save()

    def selected_rows(self) -> List[int]:
        """Return unique selected row indices."""
        model = self.table.selectionModel()
        if model is None:
            return []
        rows = {index.row() for index in model.selectedRows()}
        return sorted(rows)

    def entries(self, selected_only: bool) -> List[SplitEntry]:
        """Return split entries, optionally filtered by selection.

        Args:
            selected_only: If True, return only entries from selected rows.

        Returns:
            List of split entry definitions.
        """
        selected = self.selected_rows()
        rows = (
            selected
            if selected_only and selected
            else list(range(self.table.rowCount()))
        )
        entries: List[SplitEntry] = []
        for row in rows:
            pages_item = self.table.item(row, 1)
            title_item = self.table.item(row, 2)
            pages = pages_item.text().strip() if pages_item else ""
            title = title_item.text().strip() if title_item else ""
            if pages:
                rotation_map = (
                    dict(self._row_rotations[row])
                    if 0 <= row < len(self._row_rotations)
                    else {}
                )
                entries.append(SplitEntry(pages, title, row, rotation_map))
        return entries

    def set_generation_enabled(self, enabled: bool):
        """Enable or disable the generate button.

        Args:
            enabled: If True, enable the generate button; otherwise disable.
        """
        self.btn_generate_all.setEnabled(enabled)

    def set_paddle_available(self, enabled: bool):
        """Configure availability of the PaddleOCR backend.

        Args:
            enabled: If True, mark PaddleOCR as available.
        """
        self._paddle_available = enabled
        if not enabled and self._ocr_engine == "paddle":
            self._ocr_engine = "tesseract"

    def set_ocr_engine(self, engine: str):
        """Synchronize selected OCR engine with viewer.

        Args:
            engine: Engine name, either "tesseract" or "paddle" (if available).
        """
        if engine == "paddle" and not self._paddle_available:
            engine = "tesseract"
        if engine in self._ocr_engine_labels:
            self._ocr_engine = engine

    def set_total_pages(self, total: int):
        """Update total page indicator and seed defaults.

        Args:
            total: Total number of pages in the document.
        """
        self._total_pages = max(0, total)
        self.lbl_pages.setText(
            self._t(
                "pdf.split.pages_label",
                "Pages: {count}",
                count=self._total_pages,
            )
        )
        self._seed_default_row_if_needed()

    def set_source(self, path: Optional[str]):
        """Update label with the selected source file.

        Args:
            path: Path to the source PDF file, or None to clear.
        """
        if self._storage_enabled:
            self._flush_pending_save()
        self._source_path = path
        if path:
            name = os.path.basename(path)
            self.lbl_source.setText(
                self._t("pdf.split.source_label", "Source: {name}", name=name)
            )
        else:
            self.lbl_source.setText(
                self._t("pdf.split.source_none", "Source: none")
            )
        self._storage_enabled = bool(path and path.lower().endswith(".pdf"))
        if self._storage_enabled and not self._yaml_supported():
            self._storage_enabled = False
        self._yaml_path = (
            f"{path}.yaml" if self._storage_enabled and path else None
        )
        self._save_timer.stop()
        self._close_preview_windows()
        self._clear_rows()
        loaded = False
        if self._storage_enabled:
            loaded = self._load_yaml_state()
        if not loaded:
            self._seed_default_row_if_needed()

    def is_prefix_enabled(self) -> bool:
        """Return whether zero-padded prefixes are requested."""
        return self.chk_prefix.isChecked()

    def set_ocr_text(self, text: str):
        """Display OCR results in the text box.

        Args:
            text: Text string to append to the OCR results display.
        """
        snippet = text.strip()
        existing = self.ocr_text.toPlainText().strip()
        combined = snippet if not existing else f"{existing}\n{snippet}"
        self.ocr_text.setPlainText(combined)
        scrollbar = self.ocr_text.verticalScrollBar()
        if scrollbar is not None:
            scrollbar.setValue(scrollbar.maximum())

    def _show_context_menu(self, pos: QPoint):
        """Context menu for per-row actions.

        Args:
            pos: Viewport coordinates where the menu should appear.
        """
        viewport = self.table.viewport()
        if viewport is None:
            return
        index = self.table.indexAt(pos)
        target_row = index.row() if index.isValid() else None
        if target_row is None:
            selected = self.selected_rows()
            target_row = selected[0] if selected else None
        global_pos = viewport.mapToGlobal(pos)
        menu = QMenu(self)

        act_generate = QAction(
            self._t("pdf.split.generate_selected", "Create selected"), menu
        )
        act_generate.setEnabled(
            self.btn_generate_all.isEnabled() and bool(self.selected_rows())
        )
        act_generate.triggered.connect(self.generateSelectedRequested.emit)
        menu.addAction(act_generate)

        menu.addSeparator()

        act_add = QAction(self._t("pdf.split.add_row", "Add row"), menu)
        act_add.triggered.connect(self._handle_add_row)
        menu.addAction(act_add)

        act_remove = QAction(
            self._t("pdf.split.remove_row", "Remove selected"), menu
        )
        act_remove.setEnabled(bool(self.selected_rows()))
        act_remove.triggered.connect(self.remove_selected_rows)
        menu.addAction(act_remove)

        menu.addSeparator()

        act_move_up = QAction(self._t("pdf.split.move_up", "Move up (U)"), menu)
        selected = self.selected_rows()
        act_move_up.setEnabled(bool(selected) and selected[0] > 0)
        act_move_up.triggered.connect(self._move_rows_up)
        menu.addAction(act_move_up)

        act_move_down = QAction(
            self._t("pdf.split.move_down", "Move down (D)"), menu
        )
        max_row = self.table.rowCount() - 1
        act_move_down.setEnabled(bool(selected) and selected[-1] < max_row)
        act_move_down.triggered.connect(self._move_rows_down)
        menu.addAction(act_move_down)

        menu.addSeparator()

        page_actions_enabled = self._total_pages > 0

        act_add_page_last = QAction(
            self._t(
                "pdf.split.add_page_last",
                "Add current page to last entry",
            ),
            menu,
        )
        act_add_page_last.setEnabled(page_actions_enabled)
        act_add_page_last.triggered.connect(self._handle_add_page_last)
        menu.addAction(act_add_page_last)

        act_add_page_selected = QAction(
            self._t(
                "pdf.split.add_page_selected",
                "Add current page to selected entries",
            ),
            menu,
        )
        act_add_page_selected.setEnabled(
            page_actions_enabled and bool(self.selected_rows())
        )
        act_add_page_selected.triggered.connect(self._handle_add_page_selected)
        menu.addAction(act_add_page_selected)

        act_new_from_page = QAction(
            self._t(
                "pdf.split.new_from_page",
                "New entry from current page",
            ),
            menu,
        )
        act_new_from_page.setEnabled(page_actions_enabled)
        act_new_from_page.triggered.connect(self._handle_new_from_page)
        menu.addAction(act_new_from_page)

        if target_row is not None and target_row >= 0:
            menu.addSeparator()
            act_go_to = QAction(
                self._t(
                    "pdf.split.goto_entry",
                    "Go to first page in entry",
                ),
                menu,
            )
            act_go_to.setEnabled(self._total_pages > 0)
            act_go_to.triggered.connect(
                partial(self._navigate_to_row_start, target_row)
            )
            menu.addAction(act_go_to)

            act_preview = QAction(
                self._t("pdf.split.preview_entry", "Preview entry"), menu
            )
            act_preview.setEnabled(self._total_pages > 0)
            act_preview.triggered.connect(
                partial(self._open_preview_for_row, target_row)
            )
            menu.addAction(act_preview)

            act_edit_rotation = QAction(
                self._t(
                    "pdf.split.edit_page_rotation",
                    "Set page rotations…",
                ),
                menu,
            )
            act_edit_rotation.triggered.connect(
                partial(self._open_rotation_dialog, target_row)
            )
            menu.addAction(act_edit_rotation)

        menu.exec_(global_pos)

    def _handle_add_row(self):
        """Add a default definition row seeded with the current page."""
        current_page = max(1, self._viewer.current_page_number())
        rotation = self._viewer.current_rotation()
        rotations = {current_page: rotation} if rotation else None
        self.add_row(
            str(current_page),
            "",
            start_title_edit=True,
            rotations=rotations,
        )

    def _handle_add_page_last(self):
        """Append the current page number to the last entry."""
        page = max(1, self._viewer.current_page_number())
        rotation = self._viewer.current_rotation()
        self.add_page_to_last(page, rotation)

    def _handle_add_page_selected(self):
        """Append the current page number to the selected entries."""
        page = max(1, self._viewer.current_page_number())
        rotation = self._viewer.current_rotation()
        self.add_page_to_rows(page, rotation=rotation)

    def _handle_new_from_page(self):
        """Create a new entry that contains only the current page."""
        page = max(1, self._viewer.current_page_number())
        rotation = self._viewer.current_rotation()
        self.create_entry_for_page(page, rotation)

    def _open_rotation_dialog(self, row: int):
        """Display dialog for editing per-page rotations for a row.

        Args:
            row: Zero-based row index to edit rotations for.
        """
        if row < 0 or row >= self.table.rowCount():
            return
        pages = self._expand_pages_for_row(row, quiet=False)
        if not pages:
            QMessageBox.warning(
                self,
                self._t("pdf.split.rotations.none", "No pages detected"),
                self._t(
                    "pdf.split.rotations.none_msg",
                    "Add at least one valid page before setting rotations.",
                ),
            )
            return
        existing = (
            dict(self._row_rotations[row])
            if 0 <= row < len(self._row_rotations)
            else {}
        )
        dialog = RotationEditorDialog(self, pages, existing, translator=self._t)
        if dialog.exec_() == QDialog.Accepted:
            self._set_row_rotations(row, dialog.rotations())
            self._schedule_save()

    def _open_preview_for_row(self, row: int):
        """Open a floating window showing the pages defined by a row.

        Args:
            row: Zero-based row index to preview.
        """
        if row < 0 or row >= self.table.rowCount():
            return
        pages = self._expand_pages_for_row(row, quiet=False)
        if not pages:
            return
        rotations = (
            dict(self._row_rotations[row])
            if 0 <= row < len(self._row_rotations)
            else {}
        )
        title_item = self.table.item(row, 2)
        title = title_item.text().strip() if title_item else ""
        preview = SplitPreviewWindow(
            self._viewer,
            pages,
            rotations,
            title,
            translator=self._t,
        )
        self._preview_windows.append(preview)
        preview.destroyed.connect(
            lambda *_, ref=preview: self._remove_preview_window(ref)
        )
        preview.show()
        preview.raise_()

    def _navigate_to_row_start(self, row: int):
        """Activate the first page referenced by the provided row.

        Args:
            row: Zero-based row index to navigate to.
        """
        if row < 0 or row >= self.table.rowCount():
            return
        pages = self._expand_pages_for_row(row, quiet=False)
        if not pages:
            return
        target = min(pages)
        self._viewer.navigate_to_page(target)

    def _remove_preview_window(self, window: SplitPreviewWindow):
        """Drop bookkeeping for a preview window after it closes.

        Args:
            window: Preview window instance that was closed.
        """
        try:
            self._preview_windows.remove(window)
        except ValueError:
            pass

    def _close_preview_windows(self):
        """Close every preview window when reloading state."""
        for window in list(self._preview_windows):
            try:
                window.close()
            except RuntimeError:
                pass
        self._preview_windows.clear()

    def _show_ocr_text_menu(self, pos: QPoint):
        """Custom context menu for the OCR text box.

        Args:
            pos: Viewport coordinates where the menu should appear.
        """
        menu = self.ocr_text.createStandardContextMenu()
        if menu is None:
            return
        menu.addSeparator()

        clear_action = QAction(self._t("pdf.ocr.clear", "Clear text"), menu)
        clear_action.triggered.connect(self.ocr_text.clear)
        menu.addAction(clear_action)

        mode_menu = menu.addMenu(self._t("pdf.ocr.mode", "OCR mode"))
        if mode_menu is not None:
            for key, label in self._ocr_mode_labels.items():
                act = mode_menu.addAction(label)
                if act is None:
                    continue
                act.setCheckable(True)
                act.setChecked(self._ocr_mode == key)
                act.triggered.connect(partial(self._handle_mode_change, key))

        engine_menu = menu.addMenu(self._t("pdf.ocr.engine", "OCR engine"))
        if engine_menu is not None:
            for key in self._available_engines():
                label = self._ocr_engine_labels.get(key, key.title())
                act = engine_menu.addAction(label)
                if act is None:
                    continue
                act.setCheckable(True)
                act.setChecked(self._ocr_engine == key)
                act.triggered.connect(partial(self._handle_engine_change, key))

        menu.exec_(self.ocr_text.mapToGlobal(pos))

    def _handle_mode_change(self, mode: str, _checked: bool = False):
        """Handle OCR mode toggles.

        Args:
            mode: OCR mode identifier to switch to.
            _checked: Unused parameter for signal compatibility.
        """
        if mode == self._ocr_mode or mode not in self._ocr_mode_labels:
            return
        self._ocr_mode = mode
        self.ocrModeChanged.emit(mode)

    def _handle_engine_change(self, engine: str, _checked: bool = False):
        """Handle OCR engine selection changes.

        Args:
            engine: Engine name to switch to.
            _checked: Unused parameter for signal compatibility.
        """
        if engine == "paddle" and not self._paddle_available:
            return
        if engine == self._ocr_engine:
            return
        self._ocr_engine = engine
        self.ocrEngineChanged.emit(engine)

    def _available_engines(self) -> List[str]:
        """Return the list of engines that can be toggled.

        Returns:
            List of available OCR engine names.
        """
        engines = ["tesseract"]
        if self._paddle_available:
            engines.insert(0, "paddle")
        return engines

    # ---- Rotation & persistence helpers -------------------------------------
    def _handle_item_changed(self, item: Optional[QTableWidgetItem]):
        """Update persistence when list content changes.

        Args:
            item: Table item that was modified, or None.
        """
        if self._loading_state or item is None:
            return
        if item.column() == 1:
            self._normalize_rotations_for_row(item.row())
        self._schedule_save()

    def _handle_prefix_toggled(self, _checked: bool):
        """Persist prefix preference changes."""
        if self._loading_state:
            return
        self._schedule_save()

    def _ensure_rotation_store(self, row: int):
        """Expand rotation metadata to include the requested row.

        Args:
            row: Zero-based row index to ensure exists in the rotation store.
        """
        while len(self._row_rotations) <= row:
            self._row_rotations.append({})

    def _set_row_rotations(self, row: int, rotations: Dict[int, int]):
        """Replace rotation metadata for a specific row.

        Args:
            row: Zero-based row index.
            rotations: Dictionary mapping 1-based page numbers to rotation
                angles.
        """
        self._ensure_rotation_store(row)
        normalized: Dict[int, int] = {}
        for page, angle in rotations.items():
            try:
                page_number = int(page)
            except (TypeError, ValueError):
                continue
            rotation = self._normalize_rotation_value(angle)
            if rotation:
                normalized[page_number] = rotation
        self._row_rotations[row] = normalized

    def _set_page_rotation(self, row: int, page: int, rotation: int):
        """Store rotation metadata for a single page.

        Args:
            row: Zero-based row index.
            page: 1-based page number.
            rotation: Rotation angle in degrees.
        """
        self._ensure_rotation_store(row)
        normalized = self._normalize_rotation_value(rotation)
        if normalized:
            self._row_rotations[row][page] = normalized
        else:
            self._row_rotations[row].pop(page, None)

    def _normalize_rotation_value(self, value: int) -> int:
        """Return a normalized clockwise rotation (multiples of 90).

        Args:
            value: Rotation angle in degrees.

        Returns:
            Normalized angle (0, 90, 180, or 270), or 0 if invalid.
        """
        if not isinstance(value, int):
            return 0
        normalized = value % 360
        if normalized < 0:
            normalized += 360
        if normalized % 90 != 0:
            return 0
        return normalized

    def _expand_pages_for_row(self, row: int, quiet: bool = True) -> List[int]:
        """Expand the page expression for the provided row.

        Args:
            row: Zero-based row index to expand.
            quiet: If False, show error dialogs for invalid expressions.

        Returns:
            List of 1-based page numbers, or empty list on error.
        """
        if row < 0 or row >= self.table.rowCount():
            return []
        item = self.table.item(row, 1)
        expr = item.text().strip() if item else ""
        if not expr:
            return []
        try:
            return self._viewer.expand_page_expression(expr)
        except ValueError as exc:
            if not quiet:
                QMessageBox.warning(
                    self,
                    self._t("pdf.split.invalid_range", "Invalid page range"),
                    str(exc),
                )
            return []

    def _normalize_rotations_for_row(self, row: int):
        """Drop rotation metadata for pages no longer referenced.

        Args:
            row: Zero-based row index to normalize.
        """
        pages = set(self._expand_pages_for_row(row))
        self._ensure_rotation_store(row)
        stored = self._row_rotations[row]
        obsolete = [page for page in stored if page not in pages]
        for page in obsolete:
            stored.pop(page, None)

    def _schedule_save(self):
        """Debounce-save the table content to YAML."""
        if (
            self._loading_state
            or not self._storage_enabled
            or not self._yaml_path
        ):
            return
        if not self._yaml_supported():
            return
        self._save_timer.start()

    def _persist_to_yaml(self):
        """Write the serialized plan to disk."""
        if (
            not self._storage_enabled
            or not self._yaml_path
            or not self._yaml_supported()
        ):
            return
        data = self._serialize_rows()
        directory = os.path.dirname(self._yaml_path)
        if directory:
            try:
                os.makedirs(directory, exist_ok=True)
            except OSError as exc:
                logger.warning(
                    "Failed to create directory %s: %s", directory, exc
                )
                return
        try:
            with open(self._yaml_path, "w", encoding="utf-8") as handle:
                yaml.safe_dump(
                    data,
                    handle,
                    allow_unicode=True,
                    sort_keys=False,
                )
        except Exception as exc:  # pragma: no cover - file I/O
            logger.warning(
                "Failed to save split planner state %s: %s",
                self._yaml_path,
                exc,
            )

    def _serialize_rows(self) -> Dict[str, Any]:
        """Convert current rows into a serializable structure.

        Returns:
            Dictionary containing entries and metadata suitable for YAML export.
        """
        entries: List[Dict[str, Any]] = []
        for row in range(self.table.rowCount()):
            pages_item = self.table.item(row, 1)
            title_item = self.table.item(row, 2)
            pages = pages_item.text().strip() if pages_item else ""
            title = title_item.text().strip() if title_item else ""
            entry: Dict[str, Any] = {"pages": pages, "title": title}
            if 0 <= row < len(self._row_rotations):
                rotations = self._row_rotations[row]
                if rotations:
                    entry["rotations"] = {
                        str(page): angle for page, angle in rotations.items()
                    }
            entries.append(entry)
        return {
            "entries": entries,
            "prefix_enabled": self.chk_prefix.isChecked(),
        }

    def _load_yaml_state(self) -> bool:
        """Load a previously-saved split plan.

        Returns:
            True if state was loaded successfully, False otherwise.
        """
        if not self._yaml_path or not self._yaml_supported():
            return False
        if not os.path.exists(self._yaml_path):
            return False
        try:
            with open(self._yaml_path, "r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
        except Exception as exc:  # pragma: no cover - file I/O
            logger.warning(
                "Failed to load split planner state %s: %s",
                self._yaml_path,
                exc,
            )
            return False
        entries = data.get("entries")
        prefix = data.get("prefix_enabled")
        self._loading_state = True
        try:
            if isinstance(prefix, bool):
                self.chk_prefix.setChecked(prefix)
            if isinstance(entries, list):
                for entry in entries:
                    pages = str(entry.get("pages", ""))
                    title = str(entry.get("title", ""))
                    rotations = entry.get("rotations")
                    rotation_map = (
                        rotations if isinstance(rotations, dict) else {}
                    )
                    self.add_row(
                        pages,
                        title,
                        start_title_edit=False,
                        rotations=rotation_map,
                    )
        finally:
            self._loading_state = False
        return True

    def _flush_pending_save(self):
        """Flush any pending YAML save before switching sources."""
        if (
            not self._storage_enabled
            or not self._yaml_path
            or not self._yaml_supported()
        ):
            return
        if self._save_timer.isActive():
            self._save_timer.stop()
        self._persist_to_yaml()

    def _clear_rows(self):
        """Remove all split definitions and metadata."""
        self.table.setRowCount(0)
        self._row_rotations.clear()

    def _seed_default_row_if_needed(self):
        """Ensure a default row exists when pages are known."""
        if self.table.rowCount() > 0 or self._total_pages <= 0:
            return
        self.add_row(
            f"1-{self._total_pages}",
            self._t("pdf.split.default_title", "Entire document"),
        )

    def _yaml_supported(self) -> bool:
        """Return True if YAML persistence is available."""
        if yaml is not None:
            return True
        if not self._warned_yaml_missing:
            logger.warning(
                "PyYAML is not installed; PDF split plans will not persist."
            )
            self._warned_yaml_missing = True
        return False

    def _update_index_column(self):
        """Update all index column values to reflect current row positions."""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is None:
                item = QTableWidgetItem(str(row + 1))
                index_flags = cast(
                    Qt.ItemFlags,
                    Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable,
                )
                item.setFlags(index_flags)
                self.table.setItem(row, 0, item)
            else:
                item.setText(str(row + 1))

    def _move_rows_up(self):
        """Move selected rows up by one position."""
        selected = self.selected_rows()
        if not selected or selected[0] == 0:
            return
        # Move from top to bottom to preserve selection
        for row in selected:
            if row > 0:
                self._swap_rows(row, row - 1)
        # Restore selection after move
        for row in selected:
            if row > 0:
                self.table.selectRow(row - 1)
        self._update_index_column()
        self._schedule_save()

    def _move_rows_down(self):
        """Move selected rows down by one position."""
        selected = self.selected_rows()
        if not selected:
            return
        max_row = self.table.rowCount() - 1
        if selected[-1] >= max_row:
            return
        # Move from bottom to top to preserve selection
        for row in reversed(selected):
            if row < max_row:
                self._swap_rows(row, row + 1)
        # Restore selection after move
        for row in selected:
            if row < max_row:
                self.table.selectRow(row + 1)
        self._update_index_column()
        self._schedule_save()

    def _swap_rows(self, row1: int, row2: int):
        """Swap two rows in the table, preserving all data and rotations."""
        if row1 == row2 or row1 < 0 or row2 < 0:
            return
        if row1 >= self.table.rowCount() or row2 >= self.table.rowCount():
            return

        # Swap table items
        for col in range(self.table.columnCount()):
            item1 = self.table.takeItem(row1, col)
            item2 = self.table.takeItem(row2, col)
            if item1 is not None:
                self.table.setItem(row2, col, item1)
            if item2 is not None:
                self.table.setItem(row1, col, item2)

        # Swap rotation data
        self._ensure_rotation_store(max(row1, row2))
        if row1 < len(self._row_rotations) and row2 < len(self._row_rotations):
            self._row_rotations[row1], self._row_rotations[row2] = (
                self._row_rotations[row2],
                self._row_rotations[row1],
            )

    def eventFilter(self, a0: Optional[QObject], a1: Optional[QEvent]) -> bool:
        """Handle keyboard shortcuts for moving rows."""
        if a0 == self.table and a1 is not None:
            if a1.type() == QEvent.Type.KeyPress:  # type: ignore[attr-defined]
                key_event = cast(QKeyEvent, a1)
                # type: ignore[attr-defined]
                if key_event.key() == Qt.Key.Key_U:
                    mods = key_event.modifiers()
                    # type: ignore[attr-defined]
                    if mods == Qt.KeyboardModifier.NoModifier:
                        self._move_rows_up()
                        return True
                # type: ignore[attr-defined]
                if key_event.key() == Qt.Key.Key_D:
                    mods = key_event.modifiers()
                    # type: ignore[attr-defined]
                    if mods == Qt.KeyboardModifier.NoModifier:
                        self._move_rows_down()
                        return True
        return super().eventFilter(a0, a1)
