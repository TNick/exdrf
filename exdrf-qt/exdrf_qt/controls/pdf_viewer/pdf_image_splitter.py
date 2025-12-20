"""PDF viewer with split functionality for exporting page ranges."""

import logging
import os
import re
from typing import List, Optional, Set, Tuple

from PyQt5.QtCore import QPoint, QRect, Qt
from PyQt5.QtWidgets import QHBoxLayout, QMenu, QMessageBox, QSplitter, QWidget

from exdrf_qt.controls.pdf_viewer.pdf_image_viewer import PdfImageViewer
from exdrf_qt.controls.pdf_viewer.split_entry import SplitEntry
from exdrf_qt.controls.pdf_viewer.split_plan_panel import SplitPlanPanel

logger = logging.getLogger(__name__)


class PdfImageSplitter(PdfImageViewer):
    """PDF viewer extended with split functionality for exporting page ranges.

    Extends PdfImageViewer to add:
    - Split planner panel for defining page ranges to export
    - PDF splitting and export functionality
    - Integration with OCR text capture for split planning
    """

    def __init__(self, ctx, parent: Optional[QWidget] = None):
        """Initialize the PDF splitter with split panel.

        Args:
            ctx: Qt context for translations and icons.
            parent: Parent widget.
        """
        # Reserve split panel reference so base hooks can run safely.
        self._split_panel: Optional[SplitPlanPanel] = None
        # Track hook installation to avoid duplicate signal/event connections.
        self._viewer_hooks_installed = False
        self._split_panel_hooks_installed = False

        # Initialize base class - it creates viewer_panel in a simple layout
        super().__init__(ctx, parent)

        # Extract viewer_panel from the base class layout
        # The base class creates a QHBoxLayout with viewer_panel as the only
        # widget
        old_layout = self.layout()
        viewer_panel = None
        if old_layout is not None and old_layout.count() > 0:
            item = old_layout.itemAt(0)
            if item and item.widget():
                viewer_panel = item.widget()
                # Remove it from old layout so we can add it to splitter
                old_layout.removeWidget(viewer_panel)

        # Create split panel
        self._split_panel = SplitPlanPanel(self)
        split_panel = self._ensure_split_panel()
        split_panel.generateAllRequested.connect(self._handle_generate_all)
        split_panel.generateSelectedRequested.connect(
            self._handle_generate_selected
        )
        split_panel.ocrModeChanged.connect(self._set_ocr_mode)
        split_panel.ocrEngineChanged.connect(self._set_ocr_engine)
        split_panel.set_paddle_available(self._paddle_available)
        split_panel.set_ocr_engine(self._ocr_engine)

        # Reinstall interaction hooks with split panel
        self._install_interaction_hooks()

        # Create splitter layout
        self._splitter = QSplitter(Qt.Orientation.Horizontal, self)
        if viewer_panel is not None:
            self._splitter.addWidget(viewer_panel)
        self._splitter.addWidget(split_panel)
        self._splitter.setStretchFactor(0, 3)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setCollapsible(0, False)
        self._splitter.setCollapsible(1, False)
        self._splitter.setSizes([900, 320])

        # Replace root layout with splitter (re-use existing layout if present)
        if old_layout is not None:
            old_layout.setContentsMargins(0, 0, 0, 0)
            old_layout.setSpacing(0)
            old_layout.addWidget(self._splitter)
        else:
            root = QHBoxLayout()
            root.setContentsMargins(0, 0, 0, 0)
            root.addWidget(self._splitter)
            self.setLayout(root)

        split_panel.set_generation_enabled(False)

    def _ensure_split_panel(self) -> SplitPlanPanel:
        """Return the split panel instance once it has been created."""
        if self._split_panel is None:
            raise RuntimeError("Split panel not initialized yet.")
        return self._split_panel

    def _install_interaction_hooks(self):
        """Install event filters and context menus for shortcuts."""
        # Install viewer hooks only once to avoid duplicate signal connections.
        if not self._viewer_hooks_installed:
            super()._install_interaction_hooks()
            self._viewer_hooks_installed = True

        # Add split panel table to event filter targets once it exists.
        if self._split_panel_hooks_installed:
            return

        split_panel = self._split_panel
        if split_panel is None:
            return
        table = split_panel.table
        table.installEventFilter(self)
        table_viewport = table.viewport()
        if table_viewport is not None:
            table_viewport.installEventFilter(self)
        self._split_panel_hooks_installed = True

    def set_pdf(
        self,
        file_path: str,
        start_page: int = 0,
        dpi: int = 150,
        lookahead: int = 4,
    ):
        """Load a PDF file for viewing.

        Args:
            file_path: Path to the PDF file.
            start_page: Zero-based index of the page to display initially.
            dpi: Resolution for rendering PDF pages (default 150).
            lookahead: Number of pages to render ahead of current (default 4).
        """
        super().set_pdf(file_path, start_page, dpi, lookahead)
        # Update split panel
        total = self._image_total
        split_panel = self._ensure_split_panel()
        split_panel.set_generation_enabled(True)
        split_panel.set_total_pages(total)
        split_panel.set_source(file_path)

    def set_image(self, file_path: str):
        """Load a single image file for viewing.

        Args:
            file_path: Path to the image file.
        """
        super().set_image(file_path)
        # Split features are disabled for standalone images.
        split_panel = self._ensure_split_panel()
        split_panel.set_generation_enabled(False)
        split_panel.set_total_pages(1)
        split_panel.set_source(file_path)

    def _set_ocr_engine(self, engine: str):
        """Switch between available OCR engines.

        Args:
            engine: Engine name, either "tesseract" or "paddle" (if available).
        """
        super()._set_ocr_engine(engine)
        split_panel = self._ensure_split_panel()
        split_panel.set_ocr_engine(engine)

    def _handle_ocr_selection(self, rect: QRect):
        """Process OCR selection rectangle coming from the graphics view.

        Args:
            rect: Viewport coordinates of the selected region.
        """
        if rect is None or rect.width() < 3 or rect.height() < 3:
            return

        # Grab the selected viewport pixels and hand them to the OCR pipeline.
        viewport = self._view.viewport()
        if viewport is None:
            return
        pixmap = viewport.grab(rect)
        text = self._run_ocr_on_pixmap(pixmap)
        if text is None:
            return
        if not text.strip():
            text = self.t("pdf.ocr.empty", "No text detected.")
        split_panel = self._ensure_split_panel()
        split_panel.set_ocr_text(text.strip())

    def _handle_key_press(self, event, source) -> bool:
        """Process shortcut keys routed through the event filter.

        Args:
            event: The keyboard event to process.
            source: The widget that received the event.

        Returns:
            True if the event was handled and should not propagate.
        """
        # Let base class handle its shortcuts first
        handled = super()._handle_key_press(event, source)
        if handled:
            return True

        if event is None or self._image_total <= 0:
            return False
        modifiers = event.modifiers()
        if modifiers not in (
            Qt.KeyboardModifier.NoModifier,
            Qt.KeyboardModifiers(),
        ):
            return False
        view_targets = [self._view]
        viewport = self._view.viewport()
        if viewport is not None:
            view_targets.append(viewport)
        split_panel = self._ensure_split_panel()
        list_targets = [split_panel.table]
        table_viewport = split_panel.table.viewport()
        if table_viewport is not None:
            list_targets.append(table_viewport)
        key = event.key()
        if key in (Qt.Key.Key_A, Qt.Key.Key_N, Qt.Key.Key_S):
            if source in view_targets or source in list_targets:
                self._trigger_page_entry_action(key)
                event.accept()
                return True
            return False
        if key in (
            Qt.Key.Key_Left,
            Qt.Key.Key_Right,
            Qt.Key.Key_Up,
            Qt.Key.Key_Down,
        ):
            if source in list_targets:
                delta = -1 if key in (Qt.Key.Key_Left, Qt.Key.Key_Up) else 1
                self._adjust_active_page(delta)
                # Allow the table to continue handling the arrow press.
                return False
        if key in (Qt.Key.Key_Comma, Qt.Key.Key_Period):
            if source in list_targets:
                if key == Qt.Key.Key_Comma:
                    self.rotate_ccw()
                else:  # Qt.Key.Key_Period
                    self.rotate_cw()
                event.accept()
                return True
        return False

    def _handle_view_context_request(self, pos: QPoint):
        """Normalize context menu positions coming from the view/viewport.

        Args:
            pos: Position in the coordinate system of the sender widget.
        """
        viewport = self._view.viewport()
        if viewport is None:
            return
        source = self.sender()
        viewport_pos = pos
        if source is self._view:
            viewport_pos = self._view.mapTo(viewport, pos)
        self._show_view_context_menu(viewport_pos)

    def _show_view_context_menu(self, pos: QPoint):
        """Show the context menu for the graphics view.

        Args:
            pos: Viewport coordinates where the menu should appear.
        """
        if self._image_total <= 0:
            return
        viewport = self._view.viewport()
        if viewport is None:
            return
        menu = QMenu(self)
        act_add_last = menu.addAction(
            self.t(
                "pdf.split.add_page_last",
                "Add current page to last entry",
            )
        )
        assert act_add_last is not None
        act_add_last.triggered.connect(self._add_current_page_to_last)

        act_add_selected = menu.addAction(
            self.t(
                "pdf.split.add_page_selected",
                "Add current page to selected entries",
            )
        )
        assert act_add_selected is not None
        split_panel = self._ensure_split_panel()
        act_add_selected.setEnabled(bool(split_panel.selected_rows()))
        act_add_selected.triggered.connect(self._add_current_page_to_selection)

        act_new_entry = menu.addAction(
            self.t(
                "pdf.split.new_from_page",
                "New entry from current page",
            )
        )
        assert act_new_entry is not None
        act_new_entry.triggered.connect(self._create_entry_from_current_page)

        menu.exec_(viewport.mapToGlobal(pos))

    def _trigger_page_entry_action(self, key: int):
        """Dispatch keyboard shortcuts tied to split planner actions.

        Args:
            key: Qt key code for the pressed key.
        """
        if key == Qt.Key.Key_A:
            self._add_current_page_to_last()
        elif key == Qt.Key.Key_N:
            self._create_entry_from_current_page()
        elif key == Qt.Key.Key_S:
            self._add_current_page_to_selection()

    def _current_action_page(self) -> Optional[int]:
        """Return the 1-based page index used for split actions."""
        if self._image_total <= 0:
            return None
        source = (
            self._active_page_index
            if self._active_page_index is not None
            else self._current_index
        )
        if source < 0 or source >= self._image_total:
            return None
        return source + 1

    def _add_current_page_to_last(self):
        """Append the current page to the last split entry."""
        page = self._current_action_page()
        if page is None:
            return
        rotation = self.current_rotation()
        split_panel = self._ensure_split_panel()
        split_panel.add_page_to_last(page, rotation)

    def _add_current_page_to_selection(self):
        """Append the current page to every selected split entry."""
        page = self._current_action_page()
        if page is None:
            return
        split_panel = self._ensure_split_panel()
        rows = split_panel.selected_rows()
        if not rows:
            return
        rotation = self.current_rotation()
        split_panel.add_page_to_rows(page, rows, rotation=rotation)

    def _create_entry_from_current_page(self):
        """Create a new entry that points only to the current page."""
        page = self._current_action_page()
        if page is None:
            return
        rotation = self.current_rotation()
        split_panel = self._ensure_split_panel()
        split_panel.create_entry_for_page(page, rotation)

    # ---- Split planner -------------------------------------------------------
    def _handle_generate_all(self):
        """Generate all configured split files."""
        self._generate_from_panel(selected_only=False)

    def _handle_generate_selected(self):
        """Generate only the selected split definitions."""
        self._generate_from_panel(selected_only=True)

    def _generate_from_panel(self, selected_only: bool):
        """Dispatch split generation for panel entries.

        Args:
            selected_only: If True, generate only selected entries; otherwise
                generate all entries.
        """
        if self._source_type != "pdf":
            self.show_error(
                self.t(
                    "pdf.split.no_pdf",
                    "Load a PDF file before creating split files.",
                ),
                self.t("pdf.split.error", "Split error"),
            )
            return
        split_panel = self._ensure_split_panel()
        entries = split_panel.entries(selected_only=selected_only)
        if not entries:
            self.show_error(
                self.t(
                    "pdf.split.no_entries",
                    "No split definitions are available.",
                ),
                self.t("pdf.split.error", "Split error"),
            )
            return
        jobs = self._build_split_jobs(entries)
        if not jobs:
            return
        self._run_split_jobs(jobs)

    def _build_split_jobs(
        self, entries: List[SplitEntry]
    ) -> List[Tuple[SplitEntry, List[int]]]:
        """Validate panel entries and expand page expressions.

        Args:
            entries: List of split entry definitions to process.

        Returns:
            List of tuples containing validated entries and their page lists.
        """
        if self._image_total <= 0:
            self.show_error(
                self.t("pdf.split.no_pages", "No pages are loaded."),
                self.t("pdf.split.error", "Split error"),
            )
            return []
        jobs: List[Tuple[SplitEntry, List[int]]] = []
        for entry in entries:
            try:
                pages = self._parse_page_expression(entry.pages_expr)
            except ValueError as exc:
                self.show_error(
                    self.t(
                        "pdf.split.invalid_row",
                        "Row {row}: {error}",
                        row=entry.row_index + 1,
                        error=str(exc),
                    ),
                    self.t("pdf.split.error", "Split error"),
                )
                return []
            jobs.append((entry, pages))
        return jobs

    def expand_page_expression(self, expr: str) -> List[int]:
        """Public helper for expanding page expressions.

        Args:
            expr: Page expression string (e.g., "1-5, 10, 15-20").

        Returns:
            List of 1-based page numbers.
        """
        return self._parse_page_expression(expr)

    def _parse_page_expression(self, expr: str) -> List[int]:
        """Parse user-provided page expressions into 1-based page numbers.

        Args:
            expr: Page expression string (e.g., "1-5, 10, 15-20").

        Returns:
            List of 1-based page numbers, sorted and deduplicated.

        Raises:
            ValueError: If the expression is invalid or contains out-of-bounds
                page numbers.
        """
        expr = (expr or "").strip()
        if not expr:
            raise ValueError(self.t("pdf.split.empty", "Empty page range."))
        tokens = [tok for tok in re.split(r"[,\s]+", expr) if tok]
        if not tokens:
            raise ValueError(self.t("pdf.split.empty", "Empty page range."))
        pages: List[int] = []
        seen: Set[int] = set()
        for token in tokens:
            token = token.strip()
            if "-" in token:
                parts = token.split("-", 1)
                if len(parts) != 2:
                    raise ValueError(
                        self.t(
                            "pdf.split.invalid_token",
                            "Invalid token: {token}",
                            token=token,
                        )
                    )
                try:
                    start = int(parts[0])
                    end = int(parts[1])
                except ValueError as exc:
                    raise ValueError(
                        self.t(
                            "pdf.split.invalid_number",
                            "Invalid number in token: {token}",
                            token=token,
                        )
                    ) from exc
                if end < start:
                    start, end = end, start
                for value in range(start, end + 1):
                    if 1 <= value <= self._image_total and value not in seen:
                        pages.append(value)
                        seen.add(value)
            else:
                try:
                    value = int(token)
                except ValueError as exc:
                    raise ValueError(
                        self.t(
                            "pdf.split.invalid_number",
                            "Invalid number in token: {token}",
                            token=token,
                        )
                    ) from exc
                if 1 <= value <= self._image_total and value not in seen:
                    pages.append(value)
                    seen.add(value)
        if not pages:
            raise ValueError(
                self.t(
                    "pdf.split.out_of_bounds",
                    "All pages are outside the document bounds.",
                )
            )
        return pages

    def _run_split_jobs(self, jobs: List[Tuple[SplitEntry, List[int]]]):
        """Execute the split operations and save generated PDFs.

        Args:
            jobs: List of tuples containing split entries and their page lists.
        """
        if not jobs:
            return

        # Sanity-check that the PDF source exists before doing any work.
        if self._pdf_path is None or not os.path.exists(self._pdf_path):
            self.show_error(
                self.t(
                    "pdf.split.no_pdf",
                    "A PDF must be loaded before splitting.",
                ),
                self.t("pdf.split.error", "Split error"),
            )
            return
        try:
            import fitz  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            self.show_error(
                self.t("pdf.split.fitz_missing", "PyMuPDF is not available."),
                self.t("pdf.split.error", "Split error"),
            )
            logger.error("PyMuPDF import failed: %s", exc)
            return

        # Open the document once and accumulate all generated filenames.
        doc = fitz.open(self._pdf_path)
        base_dir = os.path.dirname(self._pdf_path) or os.getcwd()
        split_panel = self._ensure_split_panel()
        prefix_enabled = split_panel.is_prefix_enabled()
        digits = len(str(len(jobs))) if prefix_enabled else 0
        created: List[str] = []
        try:
            # Iterate through each job, copying requested pages into a new PDF.
            for idx, (entry, pages) in enumerate(jobs, start=1):
                if not pages:
                    continue
                new_doc = fitz.open()
                for page_num in pages:
                    page_idx = page_num - 1
                    if 0 <= page_idx < doc.page_count:
                        new_doc.insert_pdf(
                            doc, from_page=page_idx, to_page=page_idx
                        )
                        rotation = entry.page_rotations.get(page_num, 0)
                        if rotation and new_doc.page_count > 0:
                            target_page = new_doc[-1]
                            self._apply_export_rotation(target_page, rotation)
                title = entry.title.strip() or entry.pages_expr.strip()
                safe_title = self._safe_filename(title or f"part_{idx}")
                prefix = (
                    f"{idx:0{digits}d}. " if prefix_enabled and digits else ""
                )
                filename = f"{prefix}{safe_title}.pdf"
                out_path = os.path.join(base_dir, filename)
                suffix = 1
                while os.path.exists(out_path):
                    filename = f"{prefix}{safe_title}_{suffix}.pdf"
                    out_path = os.path.join(base_dir, filename)
                    suffix += 1
                new_doc.save(out_path)
                created.append(out_path)
                new_doc.close()
        finally:
            doc.close()

        # Communicate the outcome with a friendly dialog.
        if created:
            self._show_info(
                self.t("pdf.split.success", "Split complete"),
                self.t(
                    "pdf.split.created",
                    "Created {count} file(s) in {folder}",
                    count=len(created),
                    folder=base_dir,
                ),
            )
        else:
            self.show_error(
                self.t("pdf.split.nothing", "No files created"),
                self.t(
                    "pdf.split.nothing_msg",
                    "No valid page definitions were found.",
                ),
            )

    def _apply_export_rotation(self, page, rotation: int):
        """Apply rotation to a PyMuPDF page instance.

        Args:
            page: PyMuPDF page object to rotate.
            rotation: Rotation angle in degrees (0, 90, 180, or 270).
        """
        if rotation % 360 == 0:
            return
        setter = getattr(page, "set_rotation", None)
        if callable(setter):
            setter(rotation)
            return
        legacy = getattr(page, "setRotation", None)
        if callable(legacy):
            legacy(rotation)

    def _safe_filename(self, name: str) -> str:
        """Return a filesystem-safe filename fragment.

        Args:
            name: Original filename string that may contain invalid characters.

        Returns:
            Sanitized filename with invalid characters replaced by underscores.
        """
        cleaned = re.sub(r'[\\\\/:*?"<>|]+', "_", name).strip()
        return cleaned or "part"

    def _show_info(self, title: str, message: str):
        """Show an informational dialog.

        Args:
            title: Dialog window title.
            message: Message text to display.
        """
        QMessageBox.information(self, title, message)
