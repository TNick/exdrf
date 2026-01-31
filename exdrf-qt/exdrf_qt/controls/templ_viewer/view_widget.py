"""Custom WebEngine view for template viewer with refresh and DevTools.

This module provides a QWebEngineView subclass that filters events to
handle mouse back/forward, F5/Ctrl+F5 refresh, Ctrl+P print, and
optionally shows a DevTools window. Used by TemplViewer as the main
web view.
"""

import logging
from typing import TYPE_CHECKING, Any

from PyQt5.QtCore import QEvent, QObject, Qt, pyqtSignal
from PyQt5.QtWebEngineWidgets import QWebEngineView

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401

logger = logging.getLogger(__name__)


class WebView(QWebEngineView, QtUseContext):
    """Custom web view with back/forward, refresh, print, and DevTools.

    Installs itself as its own event filter to handle mouse back/forward
    buttons, F5 (simple refresh), Ctrl+F5 (full refresh), and Ctrl+P
    (print). Can open a separate DevTools window attached to the page.

    Signals:
        simpleRefresh: Emitted when the user presses F5 (no Ctrl).
        fullRefresh: Emitted when the user presses Ctrl+F5.
        printRequested: Emitted when the user presses Ctrl+P.

    Attributes:
        devtools_view: Optional QWebEngineView used as DevTools window;
            created on first show_devtools call, cleared when closed.
    """

    simpleRefresh = pyqtSignal()
    fullRefresh = pyqtSignal()
    printRequested = pyqtSignal()

    def __init__(self, ctx: "QtContext", *args: Any, **kwargs: Any) -> None:
        """Initialize the web view with context and install event filter.

        Args:
            ctx: Qt context for translation and settings.
            *args: Passed to QWebEngineView (e.g. parent).
            **kwargs: Passed to QWebEngineView.
        """
        super().__init__(*args, **kwargs)
        self.ctx = ctx
        self.devtools_view = None
        self.installEventFilter(self)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # type: ignore
        """Handle back/forward mouse buttons, F5, Ctrl+F5, and Ctrl+P.

        Mouse back/forward are handled here; navigation history is used
        for back/forward. ShortcutOverride and KeyPress are used for
        F5, Ctrl+F5, and Ctrl+P to emit the corresponding signals.

        Args:
            obj: Object that received the event (usually self).
            event: The event to filter.

        Returns:
            True if the event was handled and should not be propagated,
            else the result of the base eventFilter.
        """
        if event.type() == QEvent.Type.MouseButtonPress:
            history = self.history()
            if history is None:
                return super().eventFilter(obj, event)

            if event.button() == Qt.MouseButton.BackButton:
                if history.canGoBack():
                    history.back()
                event.accept()
                return True

            if event.button() == Qt.MouseButton.ForwardButton:
                if history.canGoForward():
                    history.forward()
                event.accept()
                return True

        elif event.type() == QEvent.Type.ShortcutOverride:
            if event.key() == Qt.Key.Key_F5:
                if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                    logger.debug("Full refresh requested")
                    self.fullRefresh.emit()
                else:
                    logger.debug("Simple refresh requested")
                    self.simpleRefresh.emit()
                event.accept()
                return True
            elif event.key() == Qt.Key.Key_P:
                if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                    logger.debug("Print requested")
                    self.printRequested.emit()
                event.accept()
                return True

        elif event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_F5:
                if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                    self.fullRefresh.emit()
                else:
                    self.simpleRefresh.emit()
                event.accept()
                return True

        return super().eventFilter(obj, event)

    def show_devtools(self) -> None:
        """Create the DevTools window if needed, then show and raise it.

        On first call creates a QWebEngineView, sets it as the page's
        DevTools page, and overrides its closeEvent to clear
        devtools_view. On later calls only shows and raises the window.
        """
        if not self.devtools_view:
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
        logger.debug("DevTools view shown")

    def closeEvent(self, event: QEvent) -> None:  # type: ignore
        """Close the DevTools window if open, then close the view.

        Args:
            event: The close event passed by Qt.
        """
        if self.devtools_view:
            self.devtools_view.close()
            self.devtools_view = None
        super().closeEvent(event)
        logger.debug("Web view closed")

    def _on_devtools_close(self, event: QEvent) -> None:  # type: ignore
        """Clear devtools_view when the DevTools window is closed.

        Args:
            event: The close event from the DevTools window.
        """
        self.devtools_view = None
        event.accept()
        logger.debug("DevTools view closed")
