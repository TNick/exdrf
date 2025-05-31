import logging
from importlib import resources
from typing import TYPE_CHECKING, Optional

from PyQt5.QtCore import QBuffer, QByteArray, QIODevice, QUrl
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


class ExDrfHandler(QWebEngineUrlSchemeHandler):
    """Custom URL scheme handler for exdrf://."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Buffer references to prevent GC until jobs are done
        self._buffers = []

    def requestStarted(  # type: ignore
        self,
        job: Optional[QWebEngineUrlRequestJob],
    ):
        if job is None:
            return
        req_url: "QUrl" = job.requestUrl()
        path = req_url.path()
        host = req_url.host()
        print(f"host: {host}, path: {path}")

        data: bytes
        mime: bytes

        try:
            if host in ("datatables.min.css", "bootstrap.min.css"):
                data = read_local_assets(host)
                mime = b"text/css"
            elif host in (
                "datatables.min.js",
                "jquery-3.7.1.min.js",
                "bootstrap.bundle.min.js",
                "dataTables.bootstrap5.js",
            ):
                data = read_local_assets(host)
                mime = b"application/javascript"
            else:
                data = b"404 Not Found"
                mime = b"text/plain"
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
        if not data_buffer.open(QIODevice.ReadOnly):
            logger.error(f"Failed to open QBuffer for URL {req_url.toString()}")
            job.fail(QWebEngineUrlRequestJob.Error.RequestFailed)
            return

        self._buffers.append(data_buffer)

        # def cleanup_buffer():
        #     # Remove buffer reference after job is finished
        #     try:
        #         self._buffers.remove(data_buffer)
        #     except ValueError:
        #         pass
        # job.finished.connect(cleanup_buffer)

        print(f"replying with {len(data)} bytes")
        job.reply(content_type_qba, data_buffer)
        print(f"replied with {len(data)} bytes")


class WebEnginePage(QWebEnginePage, QtUseContext):
    """A custom web engine page that can handle internal navigation requests."""

    def __init__(self, ctx: "QtContext", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ctx = ctx
        profile = QWebEngineProfile.defaultProfile()
        if profile is None:
            raise RuntimeError("Failed to get default profile")
        self.handler = ExDrfHandler(profile)
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

    def acceptNavigationRequest(self, url, _type, isMainFrame):  # type: ignore
        url_str = url.toString()
        view = self.view()
        if view is None:
            return False
        if url_str.startswith("exdrf://"):
            # Render your own content instead of navigating
            view.setHtml(f"<h1>Custom content for {url_str}</h1>")
            # Block navigation
            return False
        return super().acceptNavigationRequest(url, _type, isMainFrame)
