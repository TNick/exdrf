import logging
from typing import TYPE_CHECKING

from PyQt5.QtCore import QEvent, Qt, pyqtSignal
from PyQt5.QtWebEngineWidgets import QWebEngineView

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401

logger = logging.getLogger(__name__)


class WebView(QWebEngineView, QtUseContext):
    """A custom web view that can handle internal navigation requests.

    Signals:
        simpleRefresh: Emitted when the user presses F5.
        fullRefresh: Emitted when the user presses Ctrl+F5.
    """

    simpleRefresh = pyqtSignal()
    fullRefresh = pyqtSignal()
    printRequested = pyqtSignal()

    def __init__(self, ctx: "QtContext", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ctx = ctx
        self.devtools_view = None
        self.installEventFilter(self)

    def eventFilter(self, obj, event):  # type: ignore
        """Handle mouse press events."""
        if event.type() == QEvent.Type.MouseButtonPress:
            # These events do not show up here. The only mouse-related
            # events that show up here are:
            # - QEvent.Type.WindowActivate
            # - QEvent.Type.Deactivate
            # - QEvent.Type.Enter
            # - QEvent.Type.Leave
            # - QEvent.Type.ContextMenu
            # - QEvent.Type.Wheel? = 31
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

        elif event.type() == QEvent.Type.ShortcutOverride:
            if event.key() == Qt.Key.Key_F5:
                if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                    self.fullRefresh.emit()
                else:
                    self.simpleRefresh.emit()
                event.accept()
                return True
            elif event.key() == Qt.Key.Key_P:
                if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                    self.printRequested.emit()
                event.accept()
                return True
            # else:
            #     print(
            #         f"Event: {event.key()}, in hex"
            #         f": {hex(event.key())}"
            #     )
        elif event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_F5:
                if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                    self.fullRefresh.emit()
                else:
                    self.simpleRefresh.emit()
                event.accept()
                return True
        # else:
        #     print(f"Event: {event.type()}, in hex: {hex(event.type())}")

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
