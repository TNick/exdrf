import logging
from collections.abc import Callable
from typing import Any, Dict, List, Optional

from PyQt5.QtCore import QRect, QSize, QTimer, QUrl
from PyQt5.QtGui import QPixmap
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QApplication

logger = logging.getLogger(__name__)

ERROR_FAILED_TO_LOAD_PAGE = "Failed to load page"
ERROR_FAILED_TO_GRAB_SCREENSHOT = "Failed to grab screenshot"
ERROR_FAILED_TO_GET_PAGE_SIZE = "Failed to get page size"
ERROR_GRABBING_FAILED = "Failed to grab full page"


class FullPageGrabber:
    """Capture the content of a web page as a full-page image.

    This class is designed to be used as a callback for a QWebEngineView.
    """

    view: QWebEngineView
    _user_callback: Callable[["FullPageGrabber"], None]
    errors: List[str]
    width: Optional[int] = None
    height: Optional[int] = None
    pixmap: Optional[QPixmap] = None
    auto_close: bool = True
    js_result: Dict[str, Any] | None = None
    url: Optional[str] = None
    html: Optional[str] = None
    img_w: int = 0
    img_h: int = 0
    debug_mode: bool = False

    def __init__(
        self,
        callback: Callable[["FullPageGrabber"], None],
        url: Optional[str] = None,
        html: Optional[str] = None,
        auto_close: bool = True,
    ):
        """Create and start a full page capture.

        Args:
            url: string URL to load
            html: HTML content to load; if url is provided this is ignored
            callback: called once the screenshot is ready
            auto_close: if True, the view will be deleted when the callback
                is called
        """
        self.errors = []
        self.auto_close = auto_close
        self.view = QWebEngineView()
        self.url = url
        self.html = html

        # Set a reasonable minimum size
        self.view.setMinimumSize(400, 300)
        self.view.move(0, 0)

        # When load finishes, kick off the resize → grab sequence
        self.view.loadFinished.connect(self._on_load_finished)

        self._user_callback = callback
        if url:
            self.view.setUrl(QUrl.fromUserInput(url))
        elif html:
            self.view.setHtml(html)
        else:
            raise ValueError("Either url or html must be provided")

        QApplication.processEvents()

    def _on_load_finished(self, ok):
        if not ok:
            self.errors.append(ERROR_FAILED_TO_LOAD_PAGE)
            logger.error(ERROR_FAILED_TO_LOAD_PAGE)
            self._user_callback(self)
            return
        logger.debug("Page loaded successfully")

        # Give the renderer a few milliseconds to stabilize
        QTimer.singleShot(1000, self._measure_and_resize)
        QApplication.processEvents()

    def _js_code(self) -> str:
        return """
        (function() {
            var doc = document.documentElement;
            var w = Math.max(
                doc.scrollWidth, doc.offsetWidth, doc.clientWidth
            );
            var h = Math.max(
                doc.scrollHeight, doc.offsetHeight, doc.clientHeight
            );
            return {width: w, height: h};
        })();
        """

    def _measure_and_resize(self):
        logger.debug("Measuring content size...")

        # Run JS to get the full content size
        page = self.view.page()
        assert page is not None
        page.runJavaScript(self._js_code(), self._on_size_computed)
        QApplication.processEvents()

    def _on_size_computed(self, js_result):
        """We're informed that the size of the page has been computed.

        Args:
            size_dict: A Python dict like {'width': 1024, 'height': 3000}.
        """
        self.js_result = js_result
        if not js_result:
            self.errors.append(ERROR_FAILED_TO_GET_PAGE_SIZE)
            logger.error(ERROR_FAILED_TO_GET_PAGE_SIZE)
            self._user_callback(self)
            return

        w = int(js_result.get("width", 800) * 3)
        h = js_result.get("height", 500)
        logger.debug(f"Content size computed: {w}x{h}")

        # Ensure minimum dimensions
        w = max(w, 100)
        h = max(h, 100)

        # Some platforms have a limit on maximum widget size (e.g.
        # ~16384×16384). Apply reasonable limits.
        max_size = 66384
        if w > max_size or h > max_size:
            logger.warning(
                f"Content size {w}x{h} exceeds maximum "
                f"{max_size}x{max_size}, clamping"
            )
            w = min(w, max_size)
            h = min(h, max_size)

        self.width = w
        self.height = h

        # Resize the view so it can render the full page at once
        self.view.resize(QSize(int(w * 110 / 100), int(h * 10)))
        logger.debug(f"Resized view to: {w}x{h}")

        # Show the view temporarily for proper rendering
        self.view.show()
        QApplication.processEvents()

        # Because the resize is asynchronous, let Qt process events before
        # grabbing
        QTimer.singleShot(1000, self._grab_full_view)  # Increased delay
        QApplication.processEvents()

    def _grab_full_view(self):
        logger.debug("Taking screenshot...")
        callback_called = False
        try:
            # Ensure view is visible and properly sized
            if self.view.isHidden():
                self.view.show()
                QApplication.processEvents()

            # grab() returns a QPixmap
            # width = self.view.width()
            # height = self.view.height()
            self.pixmap = self.view.grab(
                QRect(0, 0, self.width, self.height)  # type: ignore
            )
            assert self.pixmap is not None

            if self.pixmap.isNull():
                self.errors.append(ERROR_FAILED_TO_GRAB_SCREENSHOT)
                logger.error(ERROR_FAILED_TO_GRAB_SCREENSHOT)
                self._user_callback(self)
                return

            logger.debug(
                "Screenshot captured: %sx%s",
                self.pixmap.width(),
                self.pixmap.height(),
            )

            # Hide the view again
            self.view.hide()

            # Call the user's callback with the full‐page pixmap
            # But prevent a potential exception in the callback
            # from causing the callback to be called again in the
            # exception handler below.
            callback_called = True
            self._user_callback(self)
        except Exception:
            self.errors.append(ERROR_GRABBING_FAILED)
            logger.error(ERROR_GRABBING_FAILED, exc_info=True)
            if not callback_called:
                self._user_callback(self)
        finally:
            if self.auto_close:
                self.view.deleteLater()
                self.view = None
            logger.debug("Screenshot process completed")
