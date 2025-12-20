"""High-level PDF/image viewer with navigation and OCR tools."""

import importlib
import logging
import os
import re
import shutil
import tempfile
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, cast

from PyQt5.QtCore import (
    QEvent,
    QPoint,
    QRect,
    QSize,
    Qt,
    QThread,
    QUrl,
    pyqtSignal,
)
from PyQt5.QtGui import (
    QBrush,
    QColor,
    QDesktopServices,
    QImage,
    QKeyEvent,
    QMouseEvent,
    QPen,
    QPixmap,
    QTransform,
)
from PyQt5.QtWidgets import (
    QFrame,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
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
from exdrf_qt.controls.pdf_viewer.image_graphics_view import ImageGraphicsView
from exdrf_qt.controls.pdf_viewer.pdf_render_worker import PdfRenderWorker

try:  # pragma: no cover - optional dependency
    _paddle_module = importlib.import_module("paddleocr")
    PaddleOCR = getattr(_paddle_module, "PaddleOCR", None)
except Exception:  # pragma: no cover - optional
    PaddleOCR = None

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
    - OCR capture tool for quickly extracting text snippets

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
    pageImageReady = pyqtSignal(int)

    def __init__(self, ctx: "QtContext", parent: Optional[QWidget] = None):
        """Initialize the PDF/image viewer widget.

        Args:
            ctx: Qt context for translations and icons.
            parent: Parent widget.
        """
        super().__init__(parent)

        # Keep a reference to the shared Qt context for translations/icons.
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
        self._page_items: Dict[int, QGraphicsPixmapItem] = {}
        self._item_to_page: Dict[QGraphicsPixmapItem, int] = {}
        self._selection_frames: Dict[int, QGraphicsRectItem] = {}
        self._active_page_index: Optional[int] = None
        self._ocr_enabled = False
        self._ocr_mode: str = "auto"
        self._paddle_reader: Optional[Any] = None
        self._paddle_available = PaddleOCR is not None
        self._ocr_engine: str = (
            "paddle" if self._paddle_available else "tesseract"
        )

        toolbar = self._create_toolbar()

        viewer_panel = QWidget(self)
        viewer_layout = QHBoxLayout()
        viewer_layout.setContentsMargins(0, 0, 0, 0)
        viewer_layout.setSpacing(4)
        viewer_layout.addLayout(toolbar)
        viewer_layout.addWidget(self._view)
        viewer_panel.setLayout(viewer_layout)

        self._install_interaction_hooks()

        # Root layout: just the viewer panel
        root = QHBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(viewer_panel)
        self.setLayout(root)

        self._update_nav_buttons()
        self._update_open_button()

    # ---- UI -----------------------------------------------------------------
    def _install_interaction_hooks(self):
        """Install event filters and context menus for shortcuts."""
        viewport = self._view.viewport()
        if viewport is not None:
            viewport.installEventFilter(self)
            viewport.setContextMenuPolicy(
                Qt.ContextMenuPolicy.CustomContextMenu
            )
            viewport.customContextMenuRequested.connect(
                self._handle_view_context_request
            )
        self._view.installEventFilter(self)
        self._view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._view.customContextMenuRequested.connect(
            self._handle_view_context_request
        )

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

        self.btn_ocr = QToolButton()
        self.btn_ocr.setText(self.t("pdf.ocr", "OCR"))
        self.btn_ocr.setIcon(self.get_icon("font"))
        self.btn_ocr.setCheckable(True)
        self._configure_button_size(self.btn_ocr)
        self.btn_ocr.toggled.connect(self._toggle_ocr_mode)

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
        vl.addWidget(self.btn_ocr)
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
        if enabled and self.btn_ocr.isChecked():
            self.btn_ocr.setChecked(False)
        self._view.setDragMode(
            QGraphicsView.ScrollHandDrag if enabled else QGraphicsView.NoDrag
        )

    def _toggle_ocr_mode(self, enabled: bool):
        """Toggle OCR selection mode.

        Args:
            enabled: If True, enable OCR rectangle selection; otherwise disable.
        """
        self._ocr_enabled = enabled
        if enabled and self.btn_pan.isChecked():
            self.btn_pan.setChecked(False)
        callback = self._handle_ocr_selection if enabled else None
        self._view.set_selection_mode(enabled, callback)

    def _set_ocr_mode(self, mode: str):
        """Update OCR interpretation mode based on UI selection.

        Args:
            mode: One of "auto", "digits", "letters", or "handwriting".
        """
        valid_modes = {"auto", "digits", "letters", "handwriting"}
        if mode not in valid_modes:
            return
        self._ocr_mode = mode
        logger.debug("OCR mode changed to: %s", mode)

    def _set_ocr_engine(self, engine: str):
        """Switch between available OCR engines.

        Args:
            engine: Engine name, either "tesseract" or "paddle" (if available).
        """
        supported = {"tesseract"}
        if self._paddle_available:
            supported.add("paddle")
        if engine not in supported:
            return
        if engine == "paddle" and not self._paddle_available:
            engine = "tesseract"
        if self._ocr_engine == engine:
            return
        self._ocr_engine = engine
        logger.debug("OCR engine changed to: %s", engine)

    def is_paddle_available(self) -> bool:
        """Return True if PaddleOCR backend can be used."""
        return self._paddle_available

    def eventFilter(self, obj, event):  # type: ignore
        """Intercept key and mouse events for custom shortcuts."""
        if event is None:
            return super().eventFilter(obj, event)
        if event.type() == QEvent.Type.KeyPress:
            key_event = cast(QKeyEvent, event)
            if self._handle_key_press(key_event, obj):
                return True
        if (
            obj is self._view.viewport()
            and event.type() == QEvent.Type.MouseButtonPress
        ):
            mouse_event = cast(QMouseEvent, event)
            if mouse_event.button() in (
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.RightButton,
            ):
                page_index = self._page_index_at_view_pos(mouse_event.pos())
                if page_index is not None:
                    self._set_active_page_index_only(page_index)
            return False
        return super().eventFilter(obj, event)

    def _handle_key_press(self, event: QKeyEvent, source) -> bool:
        """Process shortcut keys routed through the event filter.

        Args:
            event: The keyboard event to process.
            source: The widget that received the event.

        Returns:
            True if the event was handled and should not propagate.
        """
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
        key = event.key()
        if key in (
            Qt.Key.Key_Left,
            Qt.Key.Key_Right,
            Qt.Key.Key_Up,
            Qt.Key.Key_Down,
        ):
            if source in view_targets:
                delta = -1 if key in (Qt.Key.Key_Left, Qt.Key.Key_Up) else 1
                self._adjust_active_page(delta)
                event.accept()
                return True
        if key in (Qt.Key.Key_Comma, Qt.Key.Key_Period):
            if source in view_targets:
                if key == Qt.Key.Key_Comma:
                    self.rotate_ccw()
                else:  # Qt.Key.Key_Period
                    self.rotate_cw()
                event.accept()
                return True
        return False

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
        # Recreate the temporary workspace so stale renders do not linger.
        self._cleanup_temp_dir()
        self._temp_dir = tempfile.mkdtemp(prefix="exdrf-pdf-viewer-")

        # Reset bookkeeping so navigation and cache state align with the
        # newly requested document.
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

        # Detect page count and clamp the initial index to the document size.
        total = self._probe_pdf_pages(file_path)
        self._image_total = total
        self._current_index = max(0, min(start_page, max(0, total - 1)))
        self._active_page_index = (
            self._current_index if self._image_total > 0 else None
        )

        self._update_page_label()
        self._update_nav_buttons()
        self._update_open_button()

        # Start background rendering and show the visible window immediately.
        self._start_worker()
        self._queue_initial_render()

    def set_image(self, file_path: str):
        """Load a single image file for viewing.

        Args:
            file_path: Path to the image file.
        """
        # Copy the source into a temporary directory for consistent cleanup.
        self._cleanup_temp_dir()
        self._temp_dir = tempfile.mkdtemp(prefix="exdrf-pdf-viewer-")
        base_name = os.path.basename(file_path) or "image.png"
        out_path = os.path.join(self._temp_dir, base_name)
        try:
            shutil.copyfile(file_path, out_path)
        except Exception:
            # Fallback: attempt to load directly without copying
            out_path = file_path

        # Reset page bookkeeping for the single-image workflow.
        self._source_type = "image"
        self._pdf_path = None
        self._image_path = file_path  # Store original path
        self._dpi = 150
        self._rotation = 0
        self._image_total = 1
        self._current_index = 0
        self._active_page_index = 0
        self._page_to_path = {0: out_path}
        self._rendered_pages = {0}
        self._queued_pages = set()
        self._pix_cache.clear()

        self._update_page_label()
        self._update_nav_buttons()
        self._update_open_button()
        self._display_pages([0])
        self.pageImageReady.emit(1)

    # ---- Navigation ----------------------------------------------------------
    def next_page(self):
        """Navigate to the next page or page group."""
        step = max(1, self._pages_per_view)
        if self._current_index + step < self._image_total:
            self._current_index += step
            self._active_page_index = self._current_index
            self._update_page_label()
            self._update_nav_buttons()
            self._render_and_show_current_group()
            self._maybe_queue_lookahead(self._current_index)

    def prev_page(self):
        """Navigate to the previous page or page group."""
        step = max(1, self._pages_per_view)
        if self._current_index - step >= 0:
            self._current_index -= step
            self._active_page_index = self._current_index
            self._update_page_label()
            self._update_nav_buttons()
            self._render_and_show_current_group()
            self._maybe_queue_lookahead(self._current_index)

    def current_page_number(self) -> int:
        """Return the 1-based index of the first visible page.

        Returns:
            The current page number, defaulting to 1 when no document is loaded.
        """
        if self._image_total <= 0:
            return 1
        active_index = (
            self._active_page_index
            if self._active_page_index is not None
            else self._current_index
        )
        return min(active_index + 1, self._image_total)

    def current_rotation(self) -> int:
        """Return the rotation applied to the active page (degrees)."""
        return self._rotation

    def navigate_to_page(self, page_number: int):
        """Navigate the viewer to the requested 1-based page number.

        Args:
            page_number: 1-based index of the page that should become active.
        """
        if self._image_total <= 0:
            return
        if page_number <= 1:
            target = 0
        else:
            target = min(page_number - 1, self._image_total - 1)
        self._set_active_page(target)

    def prefetch_pages(self, pages: List[int]):
        """Queue the provided 1-based pages for rendering if needed.

        Args:
            pages: Collection of 1-based page numbers to pre-render.
        """
        if not pages or self._image_total <= 0:
            return
        if self._worker is None:
            return
        for page in pages:
            index = page - 1
            if index < 0 or index >= self._image_total:
                continue
            if index in self._rendered_pages or index in self._queued_pages:
                continue
            self._queued_pages.add(index)
            self.requestRender.emit([index])

    def get_cached_pixmap(self, page_number: int) -> Optional[QPixmap]:
        """Return the cached pixmap for the requested 1-based page.

        Args:
            page_number: 1-based page number requested by the caller.

        Returns:
            A QPixmap instance when the page image is already rendered,
            otherwise ``None``.
        """
        if self._image_total <= 0:
            return None
        index = page_number - 1
        if index < 0 or index >= self._image_total:
            return None
        path = self._page_to_path.get(index)
        if not path or not os.path.exists(path):
            return None
        pixmap = self._pix_cache.get(index)
        if pixmap is None:
            pixmap = QPixmap(path)
            if pixmap.isNull():
                return None
            self._pix_cache[index] = pixmap
        return pixmap

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

    # ---- OCR -----------------------------------------------------------------
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
        # OCR text is available but not displayed in base viewer
        # Subclasses can override to handle OCR text display

    def _run_ocr_on_pixmap(self, pixmap: QPixmap) -> Optional[str]:
        """Convert a viewport pixmap into text using OpenCV if available.

        Args:
            pixmap: The image region to extract text from.

        Returns:
            Extracted text string, or None if OCR failed or dependencies are
            missing.
        """
        # Defer to OpenCV+NumPy for pre-processing; warn if unavailable.
        try:
            import cv2  # type: ignore
            import numpy as np  # type: ignore
        except ImportError:
            logger.warning("OpenCV is not installed. OCR is unavailable.")
            return None

        # Convert the Qt pixmap into an RGBA image buffer OpenCV understands.
        image: QImage = pixmap.toImage().convertToFormat(QImage.Format_RGBA8888)
        width = image.width()
        height = image.height()
        if width == 0 or height == 0:
            return ""
        bits = image.bits()
        if bits is None:
            return ""
        ptr = cast(Any, bits)
        ptr.setsize(image.byteCount())
        array = np.frombuffer(ptr, dtype=np.uint8).reshape((height, width, 4))

        # Build RGB/greyscale derivations and enhance the bitmap for OCR.
        rgb = cv2.cvtColor(array, cv2.COLOR_RGBA2RGB)
        gray = cv2.cvtColor(array, cv2.COLOR_RGBA2GRAY)
        processed = self._prepare_ocr_bitmap(gray, cv2, np)

        text_result: Optional[str] = None

        # Use PaddleOCR when enabled before falling back to cv2 / pytesseract.
        if self._ocr_engine == "paddle" and self._paddle_available:
            text_result = self._run_paddle_ocr(rgb)

        if not text_result:
            cv2_text = getattr(cv2, "text", None)
            if cv2_text is not None:
                try:
                    ocr_engine = cv2_text.OCRTesseract_create()
                    text_result = ocr_engine.run(processed, 0)
                except Exception as exc:  # pragma: no cover - best effort
                    logger.debug("cv2.text OCR failed: %s", exc)

        if not text_result:
            try:
                import pytesseract  # type: ignore[import-untyped]

                # Allow overriding the Tesseract binary via environment.
                tess_path = os.environ.get("EXDRF_TESSERACT_PATH")
                if tess_path:
                    pytesseract.pytesseract.tesseract_cmd = tess_path
                text_result = pytesseract.image_to_string(
                    processed, config=self._tesseract_config()
                )
            except Exception as exc:  # pragma: no cover - optional dep
                logger.warning("OCR failed: %s", exc)
                return None

        return text_result

    def _run_paddle_ocr(self, rgb_image) -> Optional[str]:
        """Run PaddleOCR on the provided RGB image.

        Args:
            rgb_image: NumPy array representing the RGB image.

        Returns:
            Extracted text string, or None if PaddleOCR is unavailable or fails.
        """
        reader = self._get_paddle_reader()
        if reader is None:
            return None
        try:
            result = reader.ocr(rgb_image)
        except Exception as exc:  # pragma: no cover - optional path
            logger.warning("PaddleOCR failed: %s", exc)
            return None
        texts: List[str] = []
        for line in result:
            for i, text in enumerate(line["rec_texts"]):
                score = line["rec_scores"][i]
                if score is None or score < 0.45:
                    continue
                texts.append(text)
        return "\n".join(texts).strip()

    def _get_paddle_reader(self):
        """Instantiate and cache a PaddleOCR reader.

        Returns:
            PaddleOCR instance, or None if unavailable or initialization fails.
        """
        if not self._paddle_available or PaddleOCR is None:
            return None
        if self._paddle_reader is not None:
            return self._paddle_reader
        try:
            lang = os.environ.get("EXDRF_PADDLE_LANG", "en")
            self._paddle_reader = PaddleOCR(
                use_angle_cls=True,
                lang=lang,
            )
        except Exception as exc:  # pragma: no cover - optional path
            logger.warning("Failed to initialize PaddleOCR: %s", exc)
            self._paddle_reader = None
            self._paddle_available = False
        return self._paddle_reader

    def _prepare_ocr_bitmap(self, gray, cv2, np):
        """Improve contrast and resolution for OCR backends.

        Args:
            gray: Grayscale image array from OpenCV.
            cv2: OpenCV module reference.
            np: NumPy module reference.

        Returns:
            Processed binary image array optimized for OCR.
        """
        denoise = cv2.fastNlMeansDenoising(gray, None, 30, 7, 21)
        block_size = 41 if self._ocr_mode == "handwriting" else 31
        if block_size % 2 == 0:
            block_size += 1
        c_subtract = 7 if self._ocr_mode == "handwriting" else 11
        thresh = cv2.adaptiveThreshold(
            denoise,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            block_size,
            c_subtract,
        )
        blur = cv2.GaussianBlur(thresh, (3, 3), 0)
        kernel_size = 3 if self._ocr_mode == "handwriting" else 2
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        morph = cv2.morphologyEx(blur, cv2.MORPH_CLOSE, kernel)
        if self._ocr_mode == "handwriting":
            morph = cv2.medianBlur(morph, 3)
        enlarged = cv2.resize(
            morph,
            None,
            fx=2.0,
            fy=2.0,
            interpolation=cv2.INTER_CUBIC,
        )
        return enlarged

    def _tesseract_config(self) -> str:
        """Construct tesseract configuration for the current OCR mode.

        Returns:
            Command-line configuration string for Tesseract OCR.
        """
        base = ["--oem 1"]
        if self._ocr_mode == "handwriting":
            base.append("--psm 13")
        else:
            base.append("--psm 6")
        if self._ocr_mode == "digits":
            base.append("tessedit_char_whitelist=0123456789.,- ")
        elif self._ocr_mode == "letters":
            whitelist = (
                "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
                "ĂÂÎȘȚăâîșț "
            )
            base.append(f"tessedit_char_whitelist={whitelist}")
        return " ".join(base)

    def expand_page_expression(self, expr: str) -> List[int]:
        """Public helper for expanding page expressions.

        Args:
            expr: Page expression string (e.g., "1-5, 10, 15-20").

        Returns:
            List of 1-based page numbers.

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
            self._display_pages([index])
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
        self.pageImageReady.emit(page_index + 1)
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
        self._page_items.clear()
        self._item_to_page.clear()
        self._selection_frames.clear()
        self._active_page_index = None
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
        # Clear previous items so the scene contains only the current group.
        for it in self._pix_items:
            self._scene.removeItem(it)
        self._pix_items = []
        self._page_items.clear()
        self._item_to_page.clear()
        self._selection_frames.clear()

        # Resolve the pixmap for each requested index, keeping None placeholders
        # for pages that are still rendering.
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

        # Determine the layout grid — 1x1, 2x1, or 2x2 depending on count.
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
            page_index = indices[i]
            self._page_items[page_index] = item
            self._item_to_page[item] = page_index
            frame = QGraphicsRectItem(
                0.0,
                0.0,
                float(p.width()),
                float(p.height()),
                item,
            )
            pen = QPen(QColor(29, 110, 247))
            pen.setWidth(3)
            frame.setPen(pen)
            frame.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            frame.setZValue(1.0)
            frame.setVisible(False)
            self._selection_frames[page_index] = frame

        # Sync selection, overlays, and default fit with the refreshed scene.
        self._ensure_active_visible(indices)
        self._update_selection_overlay()
        self._fit_if_needed()

    def _ensure_active_visible(self, visible: List[int]):
        """Ensure the current active page index is part of the visible group.

        Args:
            visible: List of currently visible page indices.
        """
        if not visible:
            self._active_page_index = None
            return
        if (
            self._active_page_index is None
            or self._active_page_index not in visible
        ):
            self._active_page_index = visible[0]

    def _update_selection_overlay(self):
        """Toggle the blue contour for the active page in multi-page mode."""
        show = self._pages_per_view > 1
        active = self._active_page_index if show else None

        # Show the contour only around the active item while hiding others.
        for idx, frame in self._selection_frames.items():
            frame.setVisible(show and active is not None and idx == active)

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
        if self._image_total > 0:
            anchor = (
                self._active_page_index
                if self._active_page_index is not None
                else self._current_index
            )
            self._current_index = self._group_start_for(anchor)
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

    # ---- Interaction helpers -------------------------------------------------
    def _page_index_at_view_pos(self, pos: QPoint) -> Optional[int]:
        """Return the page index under the provided viewport position.

        Args:
            pos: Viewport coordinates to query.

        Returns:
            Zero-based page index if found, otherwise None.
        """
        item = self._view.itemAt(pos)
        while item is not None:
            # Walk up the parent chain until we reach a pixmap item.
            if isinstance(item, QGraphicsPixmapItem):
                page_index = self._item_to_page.get(item)
                if page_index is not None:
                    return page_index
            item = item.parentItem()
        return None

    def _set_active_page_index_only(self, page_index: int):
        """Update the active page without changing the current view group.

        Args:
            page_index: Zero-based page index to activate.
        """
        if self._image_total <= 0:
            return
        clamped = max(0, min(page_index, self._image_total - 1))
        if self._active_page_index == clamped:
            return
        self._active_page_index = clamped
        self._update_selection_overlay()
        self._update_page_label()

    def _set_active_page(self, page_index: int):
        """Update the active page making sure it is visible.

        Args:
            page_index: Zero-based page index to activate and display.
        """
        if self._image_total <= 0:
            return
        clamped = max(0, min(page_index, self._image_total - 1))
        self._active_page_index = clamped
        desired_start = self._group_start_for(clamped)
        if desired_start != self._current_index:
            self._current_index = desired_start
            self._update_nav_buttons()
            self._render_and_show_current_group()
            self._maybe_queue_lookahead(self._current_index)
        else:
            self._update_selection_overlay()
        self._update_page_label()

    def _group_start_for(self, index: int) -> int:
        """Return the first page index of the group that contains `index`.

        Args:
            index: Zero-based page index to find the group for.

        Returns:
            Zero-based index of the first page in the containing group.
        """
        n = max(1, self._pages_per_view)
        if n == 1:
            return index
        remainder = index % n
        start = index - remainder
        max_start = max(0, self._image_total - n)
        return min(start, max_start)

    def _adjust_active_page(self, delta: int):
        """Move the active page selection forward or backward.

        Args:
            delta: Number of pages to move (positive for forward, negative for
                backward).
        """
        if delta == 0 or self._image_total <= 0:
            return
        current = (
            self._active_page_index
            if self._active_page_index is not None
            else self._current_index
        )
        target = max(0, min(current + delta, self._image_total - 1))
        if target == current:
            return
        self._set_active_page(target)

    def _handle_view_context_request(self, pos: QPoint):
        """Normalize context menu positions coming from the view/viewport.

        Args:
            pos: Position in the coordinate system of the sender widget.
        """
        # Base class doesn't show context menu
        # Subclasses can override to add custom menus
