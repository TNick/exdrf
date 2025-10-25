import logging
import os
from datetime import datetime, timedelta
from importlib import resources
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from PyQt5.QtCore import QBuffer, QByteArray, QIODevice, QTimer, QUrl
from PyQt5.QtWebEngineCore import (
    QWebEngineUrlRequestJob,
    QWebEngineUrlScheme,
    QWebEngineUrlSchemeHandler,
)
from PyQt5.QtWebEngineWidgets import QWebEnginePage, QWebEngineProfile

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401

logger = logging.getLogger(__name__)
scheme = QWebEngineUrlScheme(b"exdrf")
scheme.setFlags(
    QWebEngineUrlScheme.LocalScheme | QWebEngineUrlScheme.LocalAccessAllowed
)
QWebEngineUrlScheme.registerScheme(scheme)
InfoMsgLevel = QWebEnginePage.JavaScriptConsoleMessageLevel.InfoMessageLevel
WarnMsgLevel = QWebEnginePage.JavaScriptConsoleMessageLevel.WarningMessageLevel
ErrorMsgLevel = QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel


def read_local_assets(path: str) -> bytes:
    src_path = resources.files(
        "exdrf_qt.controls.templ_viewer.assets"
    ).joinpath(path)
    if src_path.is_file():
        with resources.as_file(src_path) as src_file:
            if src_file.exists():
                return src_file.read_bytes()
    raise FileNotFoundError(f"File `{path}` not found in assets directory")


class ExDrfHandler(QWebEngineUrlSchemeHandler, QtUseContext):
    """Custom URL scheme handler for exdrf://.

    This class is used to handle requests for assets, attachments, and
    attachment images.

    For now the buffers are not discarded, which is a memory leak.
    There seem to be no way to detect when the job is finished.

    The collector timer is used to collect buffers that are no longer needed.
    It is started when the handler is created and runs every minute.
    When a buffer is added the time when it will be removed is set to 5 minutes
    from the current time.

    Attributes:
        _buffers: Keep a reference to buffers to prevent them from being
            garbage collected until the job is finished.
        collector_timer: Timer that runs every minute to collect buffers that
            are no longer needed.
    """

    _buffers: List[Tuple[datetime, QBuffer]]
    collector_timer: QTimer
    icon_cache: Dict[str, bytes]

    def __init__(self, ctx: "QtContext", parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self._buffers = []
        self.icon_cache = {}
        self.collector_timer = QTimer()
        self.collector_timer.timeout.connect(self.collect_buffers)
        self.collector_timer.start(1 * 60 * 1000)

    def collect_buffers(self):
        """Collect buffers that are no longer needed."""
        before = len(self._buffers)
        now = datetime.now()
        self._buffers = [(t, b) for t, b in self._buffers if t > now]
        after = len(self._buffers)
        if after < before:
            logger.debug("Discarded %d buffers", before - after)

    def get_asset(self, path: str) -> Tuple[bytes, bytes]:
        if path in ("datatables.min.css", "bootstrap.min.css"):
            data = read_local_assets(path)
            mime = b"text/css"
        elif path in (
            "datatables.min.js",
            "jquery-3.7.1.min.js",
            "bootstrap.bundle.min.js",
            "dataTables.bootstrap5.js",
        ):
            data = read_local_assets(path)
            mime = b"application/javascript"
        else:
            data = b"404 Not Found"
            mime = b"text/plain"
        return data, mime

    def get_attachment(self, path: str) -> Tuple[bytes, bytes]:
        """Get an attachment."""
        if os.path.isfile(path):
            data = read_local_assets(path)
            mime = b"application/pdf"
        else:
            logger.error(f"Attachment not found: {path}")
            data = read_local_assets("not-found.png")
            mime = b"application/png"
        return data, mime

    def get_lib_img(self, name: str) -> Tuple[bytes, bytes]:
        """Get an attachment as an image."""
        if name.upper().endswith(".PNG"):
            name = name[:-4]
        try:
            if name in self.icon_cache:
                data = self.icon_cache[name]
                mime = b"image/png"
                return data, mime
            icon = self.get_icon(name)
            if icon is not None:
                # Convert QIcon to PNG bytes
                pixmap = icon.pixmap(32, 32)
                buffer = QBuffer()
                buffer.open(QIODevice.OpenModeFlag.ReadWrite)
                pixmap.save(buffer, "PNG")
                data = buffer.data().data()
                mime = b"image/png"
                self.icon_cache[name] = data
                return data, mime
        except Exception:
            pass
        logger.error(f"Attachment icon not found: {name}")
        data = read_local_assets("not-found.png")
        mime = b"image/png"
        return data, mime

    def get_att_img(self, path: str) -> Tuple[bytes, bytes]:
        """Get an attachment as an image."""
        if os.path.isfile(path):
            data = read_local_assets(path)
            mime = b"image/png"
        else:
            logger.error(f"Attachment image not found: {path}")
            data = read_local_assets("not-found.png")
            mime = b"image/png"
        return data, mime

    def requestStarted(  # type: ignore
        self,
        job: Optional[QWebEngineUrlRequestJob],
    ):
        if job is None:
            return
        req_url: "QUrl" = job.requestUrl()
        path = req_url.path()
        host = req_url.host()

        if path.startswith("/"):
            path = path[1:]
        logger.debug("Request for host '%s' path '%s'", host, path)

        data: bytes
        mime: bytes

        try:
            if host == "assets":
                data, mime = self.get_asset(path)
            elif host == "attachments":
                data, mime = self.get_attachment(path)
            elif host == "att-img":
                data, mime = self.get_att_img(path)
            elif host == "lib-img":
                data, mime = self.get_lib_img(path)
            else:
                raise RuntimeError(f"Unknown host: {host}")
        except Exception as e:
            logger.error(
                f"Error handling request for {req_url.toString()}: {e}"
            )
            job.fail(QWebEngineUrlRequestJob.Error.RequestFailed)
            return

        # Prepare QBuffer, hold reference
        content_type_qba = QByteArray(mime)
        data_buffer = QBuffer()
        data_buffer.setData(data)
        if not data_buffer.open(QIODevice.OpenModeFlag.ReadOnly):
            logger.error(f"Failed to open QBuffer for URL {req_url.toString()}")
            job.fail(QWebEngineUrlRequestJob.Error.RequestFailed)
            return

        # Add buffer to collector list.
        five_minutes_later = datetime.now() + timedelta(minutes=5)
        self._buffers.append((five_minutes_later, data_buffer))

        # Reply to the request.
        job.reply(content_type_qba, data_buffer)
        logger.debug("replied with %d bytes", len(data))


class WebEnginePage(QWebEnginePage, QtUseContext):
    """A custom web engine page that can handle internal navigation requests."""

    handler: ExDrfHandler
    accept_navigation: bool = False

    def __init__(self, ctx: "QtContext", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ctx = ctx
        self.handler = None  # type: ignore
        profile = QWebEngineProfile.defaultProfile()
        if profile is None:
            raise RuntimeError("Failed to get default profile")
        self.setup_handler(profile)

    def setup_handler(self, profile: "QWebEngineProfile"):
        self.handler = ExDrfHandler(self.ctx, profile)
        profile.installUrlSchemeHandler(b"exdrf", self.handler)

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        # Map JS console message level to Python logging level
        if level == InfoMsgLevel:
            logger.info(
                f"JS: {message} (line {lineNumber}, source: {sourceID})"
            )
        elif level == WarnMsgLevel:
            logger.warning(
                f"JS: {message} (line {lineNumber}, source: {sourceID})"
            )
        elif level == ErrorMsgLevel:
            logger.error(
                f"JS: {message} (line {lineNumber}, source: {sourceID})"
            )
        else:
            logger.debug(
                f"JS: {message} (line {lineNumber}, source: {sourceID})"
            )

    def acceptNavigationRequest(  # type: ignore
        self, url: "QUrl", _type, isMainFrame: bool
    ) -> bool:
        """Accept navigation requests."""
        host = url.host()
        scheme = url.scheme()

        url_str = url.toString()
        logger.debug(
            "acceptNavigationRequest url=%s scheme=%s host=%s main=%s",
            url_str,
            scheme,
            host,
            isMainFrame,
        )
        view = self.view()
        if view is None:
            return False

        # Allow internal loads needed by setHtml and fallback file loads
        if not url_str or scheme in ("about", "data", "file"):
            return True

        if scheme == "exdrf":
            if host == "navigation":
                result = self.ctx.router.route(url_str)
                if isinstance(result, Exception):
                    logger.error("Error routing %s", url_str, exc_info=result)
                    view.setHtml(f"<h1>Error routing {url_str}: {result}</h1>")
                    return False
                return False
            view.setHtml(f"<h1>Custom content for {url_str}</h1>")
            return False

        if self.accept_navigation:
            return super().acceptNavigationRequest(url, _type, isMainFrame)
        else:
            view.setHtml(f"<h1>Navigation not allowed for {url_str}</h1>")
            return False
