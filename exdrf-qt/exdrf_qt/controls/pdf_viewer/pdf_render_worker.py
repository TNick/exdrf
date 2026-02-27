"""Python-thread PDF renderer used by the PDF viewer widget."""

import logging
import queue
import threading
from typing import List, Optional

from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class PdfRenderService(QObject):
    """Queue-driven renderer that emits Qt signals from Python threads."""

    pageRendered = pyqtSignal(int, str)  # page_index, image_path
    renderFinished = pyqtSignal(object)  # list of rendered page indices
    error = pyqtSignal(str)

    _pdf_path: str
    _out_dir: str
    _dpi: int
    _thread: Optional[threading.Thread]
    _stop_event: threading.Event
    _jobs: "queue.Queue[Optional[List[int]]]"

    def __init__(self, pdf_path: str, out_dir: str, dpi: int = 150):
        """Initialize and start the queue-based renderer thread."""
        super().__init__()
        self._pdf_path = pdf_path
        self._out_dir = out_dir
        self._dpi = dpi
        self._stop_event = threading.Event()
        self._jobs = queue.Queue()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="PdfRenderWorkerThread",
            daemon=True,
        )
        self._thread.start()

    def submit_pages(self, pages: List[int]) -> None:
        """Submit one render request from the GUI thread."""
        if self._stop_event.is_set():
            return
        self._jobs.put(list(pages))

    def stop(self, timeout_ms: int = 1500) -> None:
        """Stop the renderer cooperatively and wait briefly for exit."""
        self._stop_event.set()
        self._jobs.put(None)
        thread = self._thread
        if thread is not None:
            thread.join(timeout=max(0.0, timeout_ms / 1000.0))
            self._thread = None

    def _run_loop(self) -> None:
        """Process queued render jobs sequentially."""
        while not self._stop_event.is_set():
            try:
                pages = self._jobs.get(timeout=0.25)
            except queue.Empty:
                continue
            if pages is None:
                return
            self._render_pages(pages)

    def _render_pages(self, pages: List[int]) -> None:
        """Render the specified PDF pages to PNG images."""
        try:
            # Lazily import PyMuPDF so optional dependencies are tolerated.
            try:
                import fitz  # type: ignore
            except Exception:
                self.error.emit(
                    "PyMuPDF (fitz) is required to render PDF pages."
                )
                return

            # Open the document once per batch and pre-compute the scaling
            # matrix that controls the output DPI.
            doc = fitz.open(self._pdf_path)
            x_zoom = self._dpi / 72.0
            y_zoom = self._dpi / 72.0
            mat = fitz.Matrix(x_zoom, y_zoom)
            rendered: List[int] = []
            for idx in pages:
                if self._stop_event.is_set():
                    break
                try:
                    if idx < 0 or idx >= doc.page_count:
                        continue

                    # Render each requested page to PNG and record the output.
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
