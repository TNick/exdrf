"""Custom WebEngine page and exdrf:// URL scheme handler for template viewer.

This module provides the exdrf:// URL scheme (local, local-access-allowed)
and a handler that serves assets (CSS/JS), attachments, and library icons
from the template viewer. It also defines a WebEnginePage subclass that
installs this handler, forwards JavaScript console messages to Python
logging, and controls navigation (exdrf://, about/data/file, or external).
"""

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
VERBOSE = 1
scheme = QWebEngineUrlScheme(b"exdrf")
scheme.setFlags(
    QWebEngineUrlScheme.LocalScheme | QWebEngineUrlScheme.LocalAccessAllowed
)
QWebEngineUrlScheme.registerScheme(scheme)
InfoMsgLevel = QWebEnginePage.JavaScriptConsoleMessageLevel.InfoMessageLevel
WarnMsgLevel = QWebEnginePage.JavaScriptConsoleMessageLevel.WarningMessageLevel
ErrorMsgLevel = QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel


def read_local_assets(path: str) -> bytes:
    """Read a file from the templ_viewer assets package as raw bytes.

    Args:
        path: Relative path under exdrf_qt.controls.templ_viewer.assets
            (e.g. datatables.min.css, not-found.png).

    Returns:
        File contents as bytes.

    Raises:
        FileNotFoundError: If the path is not a file in the assets directory.
    """
    src_path = resources.files(
        "exdrf_qt.controls.templ_viewer.assets"
    ).joinpath(path)
    if src_path.is_file():
        with resources.as_file(src_path) as src_file:
            if src_file.exists():
                return src_file.read_bytes()
    raise FileNotFoundError(f"File `{path}` not found in assets directory")


class ExDrfHandler(QWebEngineUrlSchemeHandler, QtUseContext):
    """Custom URL scheme handler for exdrf:// requests.

    Serves assets (CSS/JS from the package), attachments by path, and
    library icons (by name, rendered from QIcon). Buffers are kept in
    _buffers so the engine can read them; a collector timer runs every
    minute and drops buffers older than 5 minutes to limit memory use.

    Attributes:
        _buffers: List of (expiry datetime, QBuffer) to keep buffers alive
            until the engine finishes; collector removes expired entries.
        collector_timer: QTimer that runs every minute and calls
            collect_buffers.
        icon_cache: Map from icon name to PNG bytes for lib-img requests.
    """

    _buffers: List[Tuple[datetime, QBuffer]]
    collector_timer: QTimer
    icon_cache: Dict[str, bytes]

    def __init__(self, ctx: "QtContext", parent=None):
        """Initialize the exdrf handler and start the buffer collector timer.

        Args:
            ctx: Qt context for e.g. icon lookup.
            parent: Optional parent for the handler.
        """
        super().__init__(parent)
        self.ctx = ctx
        self._buffers = []
        self.icon_cache = {}
        self.collector_timer = QTimer()
        self.collector_timer.timeout.connect(self.collect_buffers)
        self.collector_timer.start(1 * 60 * 1000)

    def collect_buffers(self) -> None:
        """Remove buffers whose expiry time has passed to free memory."""
        before = len(self._buffers)
        now = datetime.now()
        self._buffers = [(t, b) for t, b in self._buffers if t > now]
        after = len(self._buffers)
        if after < before:
            logger.debug("Discarded %d buffers", before - after)

    def get_asset(self, path: str) -> Tuple[bytes, bytes]:
        """Return asset bytes and MIME type for a known CSS/JS asset path.

        Args:
            path: Filename under assets (e.g. datatables.min.css).

        Returns:
            Pair (data, mime); mime is text/css or application/javascript,
            or 404 placeholder with text/plain.
        """
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
        """Return attachment bytes and MIME for a file path (PDF or placeholder).

        Args:
            path: Absolute or relative path to the attachment file.

        Returns:
            Pair (data, mime); PDF if file exists, else not-found.png and
            image/png.
        """
        if os.path.isfile(path):
            data = read_local_assets(path)
            mime = b"application/pdf"
        else:
            logger.error("Attachment not found: %s", path)
            data = read_local_assets("not-found.png")
            mime = b"application/png"
        return data, mime

    def get_lib_img(self, name: str) -> Tuple[bytes, bytes]:
        """Return PNG bytes for a library icon by name (cached).

        Strips .png suffix if present, then looks up icon via get_icon,
        renders to 32x32 PNG, and caches. On failure returns not-found.png.

        Args:
            name: Icon name (optionally with .png); used for get_icon and cache.

        Returns:
            Pair (data, mime) with image/png.
        """
        if name.upper().endswith(".PNG"):
            name = name[:-4]
        try:
            if name in self.icon_cache:
                data = self.icon_cache[name]
                mime = b"image/png"
                return data, mime
            icon = self.get_icon(name)
            if icon is not None:
                pixmap = icon.pixmap(32, 32)
                buffer = QBuffer()
                buffer.open(QIODevice.OpenModeFlag.ReadWrite)
                pixmap.save(buffer, "PNG")
                data = buffer.data().data()
                mime = b"image/png"
                self.icon_cache[name] = data
                return data, mime
        except Exception:
            logger.log(
                VERBOSE, "Failed to get lib icon %s", name, exc_info=True
            )
        logger.error("Attachment icon not found: %s", name)
        data = read_local_assets("not-found.png")
        mime = b"image/png"
        return data, mime

    def get_att_img(self, path: str) -> Tuple[bytes, bytes]:
        """Return image bytes and MIME for an attachment image path.

        Args:
            path: Path to an image file to serve.

        Returns:
            Pair (data, mime); image/png from file or not-found.png if missing.
        """
        if os.path.isfile(path):
            data = read_local_assets(path)
            mime = b"image/png"
        else:
            logger.error("Attachment image not found: %s", path)
            data = read_local_assets("not-found.png")
            mime = b"image/png"
        return data, mime

    def requestStarted(  # type: ignore
        self,
        job: Optional[QWebEngineUrlRequestJob],
    ) -> None:
        """Handle an exdrf:// request: route by host, build buffer, reply.

        Hosts: assets, attachments, att-img, lib-img. Path is taken from
        the request URL (leading slash stripped). Reply buffer is kept in
        _buffers with 5-minute expiry for the collector.

        Args:
            job: The URL request job; failed or replied here.
        """
        if job is None:
            return
        req_url: "QUrl" = job.requestUrl()
        path = req_url.path()
        host = req_url.host()

        if path.startswith("/"):
            path = path[1:]
        logger.log(VERBOSE, "Request for host '%s' path '%s'", host, path)

        data: bytes
        mime: bytes

        # Route by host and build (data, mime); fail job on error
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
                "Error handling request for %s: %s",
                req_url.toString(),
                e,
            )
            job.fail(QWebEngineUrlRequestJob.Error.RequestFailed)
            return

        # Build reply buffer and keep reference for collector
        content_type_qba = QByteArray(mime)
        data_buffer = QBuffer()
        data_buffer.setData(data)
        if not data_buffer.open(QIODevice.OpenModeFlag.ReadOnly):
            logger.error(
                "Failed to open QBuffer for URL %s", req_url.toString()
            )
            job.fail(QWebEngineUrlRequestJob.Error.RequestFailed)
            return

        five_minutes_later = datetime.now() + timedelta(minutes=5)
        self._buffers.append((five_minutes_later, data_buffer))

        job.reply(content_type_qba, data_buffer)
        logger.debug("replied with %d bytes", len(data))


class WebEnginePage(QWebEnginePage, QtUseContext):
    """Custom WebEngine page with exdrf:// handler and navigation control.

    Installs ExDrfHandler on the default profile for exdrf:// assets,
    attachments, and lib-img. Forwards JavaScript console messages to
    Python logging. Accepts or blocks navigation based on scheme and
    accept_navigation.

    Attributes:
        handler: The ExDrfHandler installed on the profile (set in
            setup_handler).
        accept_navigation: If true, allow normal navigation for non-exdrf
            URLs; if false, show "Navigation not allowed" for them.
    """

    handler: ExDrfHandler
    accept_navigation: bool = False

    def __init__(self, ctx: "QtContext", *args, **kwargs):
        """Initialize the page with context and install exdrf handler.

        Args:
            ctx: Qt context for handler and routing.
            *args: Passed to QWebEnginePage (e.g. profile, parent).
            **kwargs: Passed to QWebEnginePage.
        """
        super().__init__(*args, **kwargs)
        self.ctx = ctx
        self.handler = None  # type: ignore
        profile = QWebEngineProfile.defaultProfile()
        if profile is None:
            raise RuntimeError("Failed to get default profile")
        self.setup_handler(profile)

    def setup_handler(self, profile: "QWebEngineProfile") -> None:
        """Install ExDrfHandler on the given profile for exdrf:// scheme.

        Args:
            profile: The WebEngine profile to install the handler on.
        """
        self.handler = ExDrfHandler(self.ctx, profile)
        profile.installUrlSchemeHandler(b"exdrf", self.handler)

    def javaScriptConsoleMessage(
        self, level, message, lineNumber, sourceID
    ) -> None:
        """Forward JavaScript console messages to Python logging.

        Maps Info/Warning/Error to info/warning/error; other levels to debug.
        """
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
                "JS: %s (line %s, source: %s)", message, lineNumber, sourceID
            )

    def acceptNavigationRequest(  # type: ignore
        self, url: "QUrl", _type, isMainFrame: bool
    ) -> bool:
        """Decide whether to allow navigation to the given URL.

        Allows about/data/file and empty URL. For exdrf://, handles
        host "navigation" via ctx.router and returns False; other exdrf
        hosts get custom placeholder and False. For other schemes,
        allows only if accept_navigation is true.

        Args:
            url: The URL being navigated to.
            _type: Navigation type (unused).
            isMainFrame: Whether the request is for the main frame.

        Returns:
            True to allow navigation, False to block (and optionally
            set placeholder HTML).
        """
        host = url.host()
        scheme = url.scheme()

        url_str = url.toString()
        logger.log(
            1,
            "acceptNavigationRequest url=%s scheme=%s host=%s main=%s",
            url_str,
            scheme,
            host,
            isMainFrame,
        )
        view = self.view()
        if view is None:
            return False

        # Allow internal loads (setHtml) and file/data/about
        if not url_str or scheme in ("about", "data", "file"):
            return True

        # exdrf: route navigation host or show placeholder; always suppress
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

        # Other schemes: allow only if accept_navigation is true
        if self.accept_navigation:
            return super().acceptNavigationRequest(url, _type, isMainFrame)
        view.setHtml(f"<h1>Navigation not allowed for {url_str}</h1>")
        return False
