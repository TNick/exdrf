from PyQt5.QtWebEngineWidgets import QWebEnginePage
from typing import TYPE_CHECKING

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401


class WebEnginePage(QWebEnginePage, QtUseContext):
    """A custom web engine page that can handle internal navigation requests."""

    def __init__(self, ctx: "QtContext", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ctx = ctx

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
