import logging
from typing import TYPE_CHECKING

from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtWebEngineWidgets import QWebEngineView

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401

logger = logging.getLogger(__name__)


class WebView(QWebEngineView, QtUseContext):
    """A custom web view that can handle internal navigation requests."""

    def __init__(self, ctx: "QtContext", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ctx = ctx
        self.devtools_view = None
        self.installEventFilter(self)

    def eventFilter(self, obj, event):  # type: ignore
        """Handle mouse press events."""
        if event.type() == QEvent.Type.MouseButtonPress:
            history = self.history()
            if history is None:
                return super().eventFilter(obj, event)

            # Handle the 'Back' button
            if event.button() == Qt.MouseButton.BackButton:
                if history.canGoBack():
                    history.back()
                event.accept()
                return True  # Return True as event is handled

            # Handle the 'Forward' button
            if event.button() == Qt.MouseButton.ForwardButton:
                if history.canGoForward():
                    history.forward()
                event.accept()
                return True  # Return True as event is handled

        # Otherwise, handle as usual
        return super().eventFilter(obj, event)

    def show_devtools(self):
        if not self.devtools_view:
            # DevTools view
            self.devtools_view = QWebEngineView()
            self.devtools_view.setWindowTitle("DevTools")
            page = self.page()
            assert page is not None
            page.setDevToolsPage(self.devtools_view.page())
            self.devtools_view.closeEvent = (
                lambda event: self._on_devtools_close(event)  # type: ignore
            )
        self.devtools_view.show()
        self.devtools_view.raise_()

    def closeEvent(self, event):  # type: ignore
        if self.devtools_view:
            self.devtools_view.close()
            self.devtools_view = None
        super().closeEvent(event)

    def _on_devtools_close(self, event):  # type: ignore
        self.devtools_view = None
        event.accept()
