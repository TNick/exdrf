import logging
from typing import List

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

logger = logging.getLogger(__name__)


class PdfRenderWorker(QObject):
    """Worker that renders specific PDF pages to images in a temp directory.

    This worker runs in a separate thread to avoid blocking the UI during
    PDF page rendering. It uses PyMuPDF (fitz) to convert PDF pages to
    PNG images.

    Attributes:
        pageRendered: Signal emitted when a page is rendered. Parameters:
            page_index (int): Zero-based page index.
            image_path (str): Path to the rendered image file.
        renderFinished: Signal emitted when rendering batch completes.
            Parameters: rendered (List[int]): List of rendered page indices.
        error: Signal emitted on rendering error. Parameters: message (str).

    Attributes:
        _pdf_path: Path to the PDF file to render.
        _out_dir: Output directory for rendered images.
        _dpi: Resolution for rendering (default 150).
    """

    pageRendered = pyqtSignal(int, str)  # page_index, image_path
    renderFinished = pyqtSignal(object)  # list of rendered page indices
    error = pyqtSignal(str)

    def __init__(self, pdf_path: str, out_dir: str, dpi: int = 150):
        """Initialize the PDF render worker.

        Args:
            pdf_path: Path to the PDF file to render.
            out_dir: Output directory for rendered images.
            dpi: Resolution for rendering (default 150).
        """
        super().__init__()
        self._pdf_path = pdf_path
        self._out_dir = out_dir
        self._dpi = dpi

    @pyqtSlot(list)
    def render_pages(self, pages: List[int]):
        """Render the specified PDF pages to images.

        Args:
            pages: List of zero-based page indices to render.
        """
        try:
            try:
                import fitz  # type: ignore
            except Exception:
                self.error.emit(
                    "PyMuPDF (fitz) is required to render PDF pages."
                )
                return

            doc = fitz.open(self._pdf_path)
            x_zoom = self._dpi / 72.0
            y_zoom = self._dpi / 72.0
            mat = fitz.Matrix(x_zoom, y_zoom)
            rendered: List[int] = []
            for idx in pages:
                try:
                    if idx < 0 or idx >= doc.page_count:
                        continue
                    page = doc.load_page(idx)
                    pix = page.get_pixmap(matrix=mat, alpha=False)
                    out_path = f"{self._out_dir}/page-{idx + 1:04d}.png"
                    pix.save(out_path)
                    self.pageRendered.emit(idx, out_path)
                    rendered.append(idx)
                except Exception as e:
                    logger.error("Error rendering page %d: %s", idx, e)
            self.renderFinished.emit(rendered)
        except Exception as e:
            self.error.emit(str(e))
