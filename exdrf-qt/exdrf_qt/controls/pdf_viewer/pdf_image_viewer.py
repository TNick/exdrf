import logging
import os
import shutil
import tempfile
from typing import TYPE_CHECKING, Dict, List, Optional, Set

from PyQt5.QtCore import QSize, QThread, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices, QPixmap, QTransform
from PyQt5.QtWidgets import (
    QFrame,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from exdrf_qt.context_use import QtUseContext

from .image_graphics_view import ImageGraphicsView
from .pdf_render_worker import PdfRenderWorker


logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401


class PdfImageViewer(QWidget, QtUseContext):
    """Widget for viewing PDFs (rendered to images) or single images.

    Provides a comprehensive PDF and image viewer with features including:
    - Multi-page PDF viewing with incremental rendering
    - Single image viewing
    - Zoom in/out with mouse wheel
    - Pan with middle mouse button
    - Page navigation (previous/next)
    - Rotation (clockwise/counter-clockwise)
    - Multi-page view modes (1-up, 2-up, 4-up)
    - Fit to width/height
    - Open in external viewer/editor

    Attributes:
        requestRender: Signal emitted to request PDF page rendering.
            Parameters: pages (List[int]): List of page indices to render.

    Attributes:
        _temp_dir: Temporary directory for rendered images.
        _source_type: Type of source ("pdf" or "image").
        _pdf_path: Path to the loaded PDF file.
        _image_path: Path to the original image file.
        _image_total: Total number of pages/images.
        _current_index: Current page/image index (zero-based).
        _dpi: DPI for PDF rendering.
        _lookahead: Number of pages to render ahead of current.
        _rotation: Current rotation in degrees (0, 90, 180, 270).
        _pages_per_view: Number of pages to display simultaneously (1, 2, 4).
        _rendered_pages: Set of rendered page indices.
        _queued_pages: Set of queued page indices awaiting rendering.
        _page_to_path: Mapping of page index to image file path.
        _pix_cache: Cache of loaded QPixmap objects.
        _thread: Worker thread for PDF rendering.
        _worker: PDF render worker instance.
        _scene: Graphics scene for displaying images.
        _view: Graphics view widget.
        _pix_items: List of graphics pixmap items currently displayed.
    """

    requestRender = pyqtSignal(list)

    def __init__(self, ctx: "QtContext", parent: Optional[QWidget] = None):
        """Initialize the PDF/image viewer widget.

        Args:
            ctx: Qt context for translations and icons.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.ctx = ctx

        # State
        self._temp_dir: Optional[str] = None
        self._source_type: Optional[str] = None  # "pdf" or "image"
        self._pdf_path: Optional[str] = None
        self._image_path: Optional[str] = None  # Original image path
        self._image_total: int = 0
        self._current_index: int = 0
        self._dpi: int = 150
        self._lookahead: int = 4
        self._rotation: int = 0  # degrees, 0/90/180/270
        self._pages_per_view: int = 1
        self._rendered_pages: Set[int] = set()
        self._queued_pages: Set[int] = set()
        self._page_to_path: Dict[int, str] = {}
        self._pix_cache: Dict[int, QPixmap] = {}

        # Worker thread (created on load for PDFs)
        self._thread: Optional[QThread] = None
        self._worker: Optional[PdfRenderWorker] = None

        # UI
        self._scene = QGraphicsScene(self)
        self._view = ImageGraphicsView(self)
        self._view.setScene(self._scene)
        self._pix_items: List[QGraphicsPixmapItem] = []

        toolbar = self._create_toolbar()

        # Root layout: vertical toolbar on the left, viewer on the right.
        root = QHBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)
        root.addLayout(toolbar)
        root.addWidget(self._view)
        self.setLayout(root)

        self._update_nav_buttons()
        self._update_open_button()

    # ---- UI -----------------------------------------------------------------
    def _create_toolbar(self) -> QVBoxLayout:
        """Create and configure the vertical toolbar.

        Returns:
            Vertical layout containing all toolbar buttons.
        """
        self.btn_prev = QToolButton()
        self.btn_prev.setText(self.t("pdf.prev", "Prev"))
        self.btn_prev.setIcon(self.get_icon("resultset_previous"))
        self._configure_button_size(self.btn_prev)
        self.btn_prev.clicked.connect(self.prev_page)

        self.lbl_page = QLabel(
            self.t(
                "pdf.page_single",
                "{current} / {total}",
                current=0,
                total=0,
            )
        )
        self.lbl_page.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        self.btn_next = QToolButton()
        self.btn_next.setText(self.t("pdf.next", "Next"))
        self.btn_next.setIcon(self.get_icon("resultset_next"))
        self._configure_button_size(self.btn_next)
        self.btn_next.clicked.connect(self.next_page)

        sep1 = self._v_sep()

        # View mode buttons: 1-up, 2-up, 4-up
        self.btn_1up = QToolButton()
        self.btn_1up.setText(self.t("pdf.1up", "1 up"))
        self.btn_1up.setIcon(self.get_icon("column_single"))
        self.btn_1up.setCheckable(True)
        self.btn_1up.setChecked(True)
        self._configure_button_size(self.btn_1up)
        self.btn_1up.clicked.connect(lambda: self.set_pages_per_view(1))

        self.btn_2up = QToolButton()
        self.btn_2up.setText(self.t("pdf.2up", "2 up"))
        self.btn_2up.setIcon(self.get_icon("column_double"))
        self.btn_2up.setCheckable(True)
        self._configure_button_size(self.btn_2up)
        self.btn_2up.clicked.connect(lambda: self.set_pages_per_view(2))

        self.btn_4up = QToolButton()
        self.btn_4up.setText(self.t("pdf.4up", "4 up"))
        self.btn_4up.setIcon(self.get_icon("column_four"))
        self.btn_4up.setCheckable(True)
        self._configure_button_size(self.btn_4up)
        self.btn_4up.clicked.connect(lambda: self.set_pages_per_view(4))

        sep_modes = self._v_sep()

        self.btn_zoom_out = QToolButton()
        self.btn_zoom_out.setText(self.t("pdf.zoom_out", "Zoom -"))
        self.btn_zoom_out.setIcon(self.get_icon("magnifier_zoom_out"))
        self._configure_button_size(self.btn_zoom_out)
        self.btn_zoom_out.clicked.connect(self.zoom_out)

        self.btn_zoom_in = QToolButton()
        self.btn_zoom_in.setText(self.t("pdf.zoom_in", "Zoom +"))
        self.btn_zoom_in.setIcon(self.get_icon("magnifier_zoom_in"))
        self._configure_button_size(self.btn_zoom_in)
        self.btn_zoom_in.clicked.connect(self.zoom_in)

        self.btn_fit_w = QToolButton()
        self.btn_fit_w.setText(self.t("pdf.fit_w", "Fit W"))
        self.btn_fit_w.setIcon(self.get_icon("size_horizontal"))
        self._configure_button_size(self.btn_fit_w)
        self.btn_fit_w.clicked.connect(self.fit_width)

        self.btn_fit_h = QToolButton()
        self.btn_fit_h.setText(self.t("pdf.fit_h", "Fit H"))
        self.btn_fit_h.setIcon(self.get_icon("size_vertical"))
        self._configure_button_size(self.btn_fit_h)
        self.btn_fit_h.clicked.connect(self.fit_height)

        self.btn_pan = QToolButton()
        self.btn_pan.setText(self.t("pdf.pan", "Pan"))
        self.btn_pan.setIcon(self.get_icon("hand"))
        self.btn_pan.setCheckable(True)
        self._configure_button_size(self.btn_pan)
        self.btn_pan.toggled.connect(self._toggle_pan_mode)

        sep2 = self._v_sep()

        self.btn_rot_ccw = QToolButton()
        self.btn_rot_ccw.setText(self.t("pdf.rot_ccw", "Rotate CCW"))
        self.btn_rot_ccw.setIcon(self.get_icon("shape_rotate_anticlockwise"))
        self._configure_button_size(self.btn_rot_ccw)
        self.btn_rot_ccw.clicked.connect(self.rotate_ccw)

        self.btn_rot_cw = QToolButton()
        self.btn_rot_cw.setText(self.t("pdf.rot_cw", "Rotate CW"))
        self.btn_rot_cw.setIcon(self.get_icon("shape_rotate_clockwise"))
        self._configure_button_size(self.btn_rot_cw)
        self.btn_rot_cw.clicked.connect(self.rotate_cw)

        sep3 = self._v_sep()

        self.btn_open_external = QToolButton()
        self.btn_open_external.setText(self.t("pdf.open_external", "Open"))
        self.btn_open_external.setIcon(self.get_icon("eye"))
        self._configure_button_size(self.btn_open_external)
        self.btn_open_external.clicked.connect(self.open_in_external_viewer)

        vl = QVBoxLayout()
        vl.setContentsMargins(6, 6, 6, 6)
        vl.setSpacing(6)
        vl.addWidget(self.btn_prev)
        vl.addWidget(self.lbl_page)
        vl.addWidget(self.btn_next)
        vl.addWidget(sep1)
        vl.addWidget(self.btn_1up)
        vl.addWidget(self.btn_2up)
        vl.addWidget(self.btn_4up)
        vl.addWidget(sep_modes)
        vl.addWidget(self.btn_zoom_out)
        vl.addWidget(self.btn_zoom_in)
        vl.addWidget(self.btn_fit_w)
        vl.addWidget(self.btn_fit_h)
        vl.addWidget(self.btn_pan)
        vl.addWidget(sep2)
        vl.addWidget(self.btn_rot_ccw)
        vl.addWidget(self.btn_rot_cw)
        vl.addWidget(sep3)
        vl.addWidget(self.btn_open_external)
        vl.addStretch(1)
        return vl

    def _v_sep(self) -> QWidget:
        """Create a vertical separator widget.

        Returns:
            A horizontal line frame widget for visual separation.
        """
        w = QFrame()
        w.setFrameShape(QFrame.HLine)
        w.setFrameShadow(QFrame.Sunken)
        return w

    def _configure_button_size(self, btn: QToolButton):
        """Configure button to be larger with icon and text.

        Args:
            btn: Tool button to configure.
        """
        btn.setMinimumSize(48, 48)
        btn.setIconSize(QSize(32, 32))
        # ToolButtonTextUnderIcon = 4
        btn.setToolButtonStyle(4)  # type: ignore

    def _toggle_pan_mode(self, enabled: bool):
        """Toggle pan mode for the graphics view.

        Args:
            enabled: If True, enable scroll hand drag mode; otherwise disable.
        """
        self._view.setDragMode(
            QGraphicsView.ScrollHandDrag if enabled else QGraphicsView.NoDrag
        )

    # ---- Public API ----------------------------------------------------------
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
        self._cleanup_temp_dir()
        self._temp_dir = tempfile.mkdtemp(prefix="exdrf-pdf-viewer-")

        self._source_type = "pdf"
        self._pdf_path = file_path
        self._image_path = None  # Clear image path when loading PDF
        self._dpi = dpi
        self._lookahead = max(0, lookahead)
        self._rotation = 0
        self._pages_per_view = max(1, min(self._pages_per_view, 4))
        self._rendered_pages.clear()
        self._queued_pages.clear()
        self._page_to_path.clear()
        self._pix_cache.clear()

        total = self._probe_pdf_pages(file_path)
        self._image_total = total
        self._current_index = max(0, min(start_page, max(0, total - 1)))
        self._update_page_label()
        self._update_nav_buttons()
        self._update_open_button()

        self._start_worker()
        self._queue_initial_render()

    def set_image(self, file_path: str):
        """Load a single image file for viewing.

        Args:
            file_path: Path to the image file.
        """
        self._cleanup_temp_dir()
        self._temp_dir = tempfile.mkdtemp(prefix="exdrf-pdf-viewer-")
        base_name = os.path.basename(file_path) or "image.png"
        out_path = os.path.join(self._temp_dir, base_name)
        try:
            shutil.copyfile(file_path, out_path)
        except Exception:
            # Fallback: attempt to load directly without copying
            out_path = file_path

        self._source_type = "image"
        self._pdf_path = None
        self._image_path = file_path  # Store original path
        self._dpi = 150
        self._rotation = 0
        self._image_total = 1
        self._current_index = 0
        self._page_to_path = {0: out_path}
        self._rendered_pages = {0}
        self._queued_pages = set()
        self._pix_cache.clear()

        self._update_page_label()
        self._update_nav_buttons()
        self._update_open_button()
        self._display_page(0)

    # ---- Navigation ----------------------------------------------------------
    def next_page(self):
        """Navigate to the next page or page group."""
        step = max(1, self._pages_per_view)
        if self._current_index + step < self._image_total:
            self._current_index += step
            self._update_page_label()
            self._update_nav_buttons()
            self._render_and_show_current_group()
            self._maybe_queue_lookahead(self._current_index)

    def prev_page(self):
        """Navigate to the previous page or page group."""
        step = max(1, self._pages_per_view)
        if self._current_index - step >= 0:
            self._current_index -= step
            self._update_page_label()
            self._update_nav_buttons()
            self._render_and_show_current_group()
            self._maybe_queue_lookahead(self._current_index)

    # ---- Transformations -----------------------------------------------------
    def zoom_in(self):
        """Zoom in on the current view."""
        self._view.zoom_in()
        self._update_pannable_bounds()

    def zoom_out(self):
        """Zoom out from the current view."""
        self._view.zoom_out()
        self._update_pannable_bounds()

    def rotate_cw(self):
        """Rotate the current view clockwise by 90 degrees."""
        self._rotation = (self._rotation + 90) % 360
        self._apply_rotation()

    def rotate_ccw(self):
        """Rotate the current view counter-clockwise by 90 degrees."""
        self._rotation = (self._rotation - 90) % 360
        self._apply_rotation()

    def open_in_external_viewer(self):
        """Open the current file in the system's default viewer/editor."""
        file_path = None
        if self._source_type == "pdf" and self._pdf_path:
            file_path = self._pdf_path
        elif self._source_type == "image" and self._image_path:
            file_path = self._image_path

        if not file_path or not os.path.exists(file_path):
            self.show_error(
                self.t("pdf.open_external.error", "Error"),
                self.t(
                    "pdf.open_external.error_msg",
                    "File not found or not loaded.",
                ),
            )
            return

        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
        except Exception as e:
            logger.error("Failed to open file in external viewer: %s", e)
            self.show_error(
                self.t("pdf.open_external.error", "Error"),
                self.t(
                    "pdf.open_external.error_msg2",
                    "Failed to open file: {error}",
                    error=str(e),
                ),
            )

    def fit_width(self):
        """Fit current content to the view width, preserving aspect ratio."""
        vr = self._scene.itemsBoundingRect()
        if vr.width() <= 0:
            return
        vp = self._view.viewport()
        if vp is None:
            return
        vw = vp.width()
        pad = 12
        target = max(0.01, (vw - pad) / vr.width())
        self._view.reset_zoom(target)
        self._update_pannable_bounds()

    def fit_height(self):
        """Fit current content to the view height, preserving aspect ratio."""
        vr = self._scene.itemsBoundingRect()
        if vr.height() <= 0:
            return
        vp = self._view.viewport()
        if vp is None:
            return
        vh = vp.height()
        pad = 12
        target = max(0.01, (vh - pad) / vr.height())
        self._view.reset_zoom(target)
        self._update_pannable_bounds()

    # ---- Internals: worker/rendering ----------------------------------------
    def _probe_pdf_pages(self, file_path: str) -> int:
        """Probe the PDF file to get the total number of pages.

        Args:
            file_path: Path to the PDF file.

        Returns:
            Total number of pages, or 0 on error.
        """
        try:
            import fitz  # type: ignore
        except Exception as e:
            logger.error("PyMuPDF (fitz) is not available: %s", e)
            return 0
        try:
            doc = fitz.open(file_path)
            return int(doc.page_count)
        except Exception as e:
            logger.error("Failed to open PDF: %s", e)
            return 0

    def _start_worker(self):
        """Start the PDF rendering worker thread."""
        self._stop_worker()
        if self._pdf_path is None or self._temp_dir is None:
            return
        self._thread = QThread(self)
        self._worker = PdfRenderWorker(
            self._pdf_path, self._temp_dir, self._dpi
        )
        self._worker.moveToThread(self._thread)
        self._thread.start()
        self._worker.pageRendered.connect(self._on_page_rendered)
        self._worker.renderFinished.connect(self._on_render_finished)
        self._worker.error.connect(self._on_render_error)
        # Bridge: emit from GUI -> worker slot in its thread
        self.requestRender.connect(self._worker.render_pages)

    def _stop_worker(self):
        """Stop and cleanup the PDF rendering worker thread."""
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(1500)
            self._thread = None
            self._worker = None

    def _queue_initial_render(self):
        """Queue the initial page rendering for the current view."""
        if self._worker is None or self._thread is None:
            return
        pages = self._build_render_window(self._current_index)
        self._queued_pages.update(pages)
        self.requestRender.emit(pages)
        self._render_and_show_current_group()

    def _maybe_queue_lookahead(self, center_index: int):
        """Queue pages for rendering based on lookahead window.

        Args:
            center_index: Center page index for the lookahead window.
        """
        if self._worker is None or self._thread is None:
            return
        pages = self._build_render_window(center_index)
        pages = [
            p
            for p in pages
            if p not in self._rendered_pages and p not in self._queued_pages
        ]
        if not pages:
            return
        self._queued_pages.update(pages)
        self.requestRender.emit(pages)

    def _build_render_window(self, center: int) -> List[int]:
        """Build a list of page indices to render around a center page.

        Args:
            center: Center page index.

        Returns:
            List of page indices to render.
        """
        if self._image_total <= 0:
            return []
        start = max(0, center - 1)
        end = min(self._image_total - 1, center + self._lookahead)
        return list(range(start, end + 1))

    def _ensure_page_ready(self, index: int):
        """Ensure a page is rendered or queued for rendering.

        Args:
            index: Page index to ensure is ready.
        """
        if index in self._rendered_pages:
            self._display_page(index)
            return
        # Ensure it's queued
        self._maybe_queue_lookahead(index)

    # ---- Slots from worker ---------------------------------------------------
    def _on_page_rendered(self, page_index: int, image_path: str):
        """Handle page rendered signal from worker.

        Args:
            page_index: Zero-based page index that was rendered.
            image_path: Path to the rendered image file.
        """
        self._rendered_pages.add(page_index)
        self._page_to_path[page_index] = image_path
        if page_index in self._visible_indices():
            self._render_and_show_current_group()

    def _on_render_finished(self, rendered: List[int]):
        """Handle render finished signal from worker.

        Args:
            rendered: List of rendered page indices.
        """

    def _on_render_error(self, message: str):
        """Handle render error signal from worker.

        Args:
            message: Error message.
        """
        logger.error("PDF render error: %s", message)
        self._scene.clear()
        self._pix_items = []
        self._view.reset_zoom(1.0)
        self.lbl_page.setText(
            self.t("pdf.render_error", "Error: {msg}", msg=message)
        )

    # ---- Display -------------------------------------------------------------
    def _display_pages(self, indices: List[int]):
        """Display the specified pages in a grid layout.

        Args:
            indices: List of page indices to display.
        """
        # Clear previous items
        for it in self._pix_items:
            self._scene.removeItem(it)
        self._pix_items = []

        # Create items for available indices
        pix_maps: List[Optional[QPixmap]] = []
        for idx in indices:
            path = self._page_to_path.get(idx)
            if path and os.path.exists(path):
                pix = self._pix_cache.get(idx)
                if pix is None:
                    pix = QPixmap(path)
                    self._pix_cache[idx] = pix
                pix_maps.append(pix)
            else:
                pix_maps.append(None)

        # Layout grid (2-up -> 2x1, 4-up -> 2x2)
        n = len(indices)
        cols = 1 if n == 1 else 2
        gap = 16

        # Compute effective dimensions after rotation
        # For 90/270 degrees, width and height are swapped
        is_rotated_90_270 = self._rotation in (90, 270)

        # Compute max w/h among available pix-maps (using effective size)
        max_w = 0
        max_h = 0
        for p in pix_maps:
            if p is not None:
                orig_w = p.width()
                orig_h = p.height()
                if is_rotated_90_270:
                    # After rotation, dimensions are swapped
                    eff_w = orig_h
                    eff_h = orig_w
                else:
                    eff_w = orig_w
                    eff_h = orig_h
                max_w = max(max_w, eff_w)
                max_h = max(max_h, eff_h)

        # Create and place items
        for i, p in enumerate(pix_maps):
            if p is None:
                continue
            item = QGraphicsPixmapItem()
            item.setPixmap(p)
            self._scene.addItem(item)
            self._pix_items.append(item)

            # Set transform origin before applying rotation
            # Use the center of the pixmap (before rotation)
            item.setTransformOriginPoint(p.width() / 2.0, p.height() / 2.0)

            # Apply rotation transform
            transform = QTransform()
            transform.rotate(self._rotation)
            item.setTransform(transform)

            # Position based on effective dimensions
            # (rotation already applied, so use pre-calculated max dimensions)
            r = i // cols
            c = i % cols
            x = float(c * (max_w + gap))
            y = float(r * (max_h + gap))
            item.setPos(x, y)

        self._fit_if_needed()

    def _apply_rotation(self):
        """Apply rotation to all pixmap items and re-layout if needed."""
        # If we have items, we need to re-layout after rotation
        if self._pix_items:
            # Get current visible indices to re-display with new rotation
            vis = self._visible_indices()
            if vis:
                self._display_pages(vis)
        else:
            # No items yet, just update bounds
            self._update_pannable_bounds()

    def _fit_if_needed(self):
        """Fit content if needed (reset zoom on first display)."""
        if self._view._zoom == 1.0:
            self._view.reset_zoom(1.0)
        self._update_pannable_bounds()

    # ---- UI helpers ----------------------------------------------------------
    def _update_page_label(self):
        """Update the page label with current page information."""
        vis = self._visible_indices()
        if not vis:
            self.lbl_page.setText(
                self.t(
                    "pdf.page_single",
                    "{current} / {total}",
                    current=0,
                    total=0,
                )
            )
            return

        a = vis[0] + 1
        b = vis[-1] + 1
        if len(vis) == 1:
            self.lbl_page.setText(
                self.t(
                    "pdf.page_single",
                    "{current} / {total}",
                    current=a,
                    total=self._image_total,
                )
            )
        else:
            self.lbl_page.setText(
                self.t(
                    "pdf.page_range",
                    "{start}-{end} / {total}",
                    start=a,
                    end=b,
                    total=self._image_total,
                )
            )

    def _update_nav_buttons(self):
        """Update navigation button states based on current position."""
        self.btn_prev.setEnabled(self._current_index > 0)
        self.btn_next.setEnabled(self._current_index + 1 < self._image_total)

    def _update_open_button(self):
        """Update the open external button state."""
        has_file = (self._source_type == "pdf" and self._pdf_path) or (
            self._source_type == "image" and self._image_path
        )
        self.btn_open_external.setEnabled(bool(has_file))

    # ---- Cleanup -------------------------------------------------------------
    def _cleanup_temp_dir(self):
        """Clean up temporary directory and stop worker thread."""
        self._stop_worker()
        if self._temp_dir and os.path.isdir(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir, ignore_errors=True)
            except Exception as e:
                logger.debug("Failed to cleanup temp dir: %s", e)
        self._temp_dir = None

    def closeEvent(self, a0):
        """Handle widget close event.

        Args:
            a0: Close event.
        """
        self._cleanup_temp_dir()
        super().closeEvent(a0)

    def resizeEvent(self, a0):
        """Handle widget resize event.

        Args:
            a0: Resize event.
        """
        self._update_pannable_bounds()
        super().resizeEvent(a0)

    # ---- Multi-page helpers --------------------------------------------------
    def set_pages_per_view(self, n: int):
        """Set the number of pages to display simultaneously.

        Args:
            n: Number of pages (1, 2, or 4).
        """
        n = 1 if n < 2 else (4 if n >= 4 else 2)
        self._pages_per_view = n
        # Update toggle state
        self.btn_1up.setChecked(n == 1)
        self.btn_2up.setChecked(n == 2)
        self.btn_4up.setChecked(n == 4)
        self._update_page_label()
        self._render_and_show_current_group()
        self._maybe_queue_lookahead(self._current_index)

    def _visible_indices(self) -> List[int]:
        """Get the list of page indices currently visible.

        Returns:
            List of zero-based page indices for the current view.
        """
        result: List[int] = []
        n = max(1, self._pages_per_view)
        for i in range(n):
            idx = self._current_index + i
            if 0 <= idx < self._image_total:
                result.append(idx)
        return result

    def _render_and_show_current_group(self):
        """Render and display the current page group."""
        vis = self._visible_indices()
        # Ensure queued
        for idx in vis:
            if idx not in self._rendered_pages:
                if idx not in self._queued_pages:
                    self._queued_pages.add(idx)
                    self.requestRender.emit([idx])
        # Show available items
        self._display_pages(vis)

    def _update_pannable_bounds(self):
        """Update scene rect to allow free panning when content is small."""
        vr = self._scene.itemsBoundingRect()
        if vr.isNull():
            return
        vp = self._view.viewport()
        if vp is None or self._view._zoom <= 0:
            return
        # Convert viewport size to scene coordinates via current zoom
        vw_scene = vp.width() / self._view._zoom
        vh_scene = vp.height() / self._view._zoom
        # Add margins only when content is smaller than the viewport
        margin_w = max(0.0, (vw_scene - vr.width()) / 2.0) + 8.0
        margin_h = max(0.0, (vh_scene - vr.height()) / 2.0) + 8.0
        expanded = vr.adjusted(-margin_w, -margin_h, margin_w, margin_h)
        self._scene.setSceneRect(expanded)
