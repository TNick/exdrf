"""Simple pane that renders merged payload as a key-value table (HTML).

Used as the result tab in merge mode. Refreshes when refresh() is called
or when the tab is shown (if connected).
"""

import html
from typing import Any, Callable, Dict, Optional

from PySide6.QtWidgets import (
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
except ImportError:
    QWebEngineView = None  # type: ignore[misc, assignment]


class CmpResultPreviewPane(QWidget):
    """Simple pane that renders merged payload as a key-value table (HTML).

    Used as the result tab in merge mode. Refreshes when refresh() is called
    or when the tab is shown (if connected).

    Attributes:
        _get_context: Callable that returns the preview context (flat key ->
            value dict).
        _view: QWebEngineView or QTextEdit used to display the HTML.
    """

    _get_context: Callable[[], Dict[str, Any]]
    _view: Optional[Any]

    def __init__(
        self,
        get_context: Callable[[], Dict[str, Any]],
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the preview pane.

        Args:
            get_context: Callable that returns the preview context (e.g. flat
                key -> value from get_result_preview_context).
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._get_context = get_context
        self._view = None

        # Build layout and choose web engine or plain text view.
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if QWebEngineView is not None:
            self._view = QWebEngineView(self)
            layout.addWidget(self._view)
        else:
            self._view = QTextEdit(self)
            self._view.setReadOnly(True)
            layout.addWidget(self._view)
        self.refresh()

    def refresh(self) -> None:
        """Rebuild HTML from current context and display it."""
        data = self._get_context()
        html_content = self._build_html(data)

        # Update the view with the new HTML content.
        if self._view is not None:
            if QWebEngineView is not None and isinstance(
                self._view, QWebEngineView
            ):
                self._view.setHtml(html_content)
            elif isinstance(self._view, QTextEdit):
                self._view.setHtml(html_content)

    def _build_html(self, data: Dict[str, Any]) -> str:
        """Build a simple key-value table HTML string."""
        rows = []

        # Build table rows from sorted key-value pairs.
        for k, v in sorted(data.items()):
            disp = "" if v is None else html.escape(str(v))
            rows.append(
                "<tr><td>%s</td><td>%s</td></tr>" % (html.escape(k), disp)
            )
        body = (
            "<table border='1' cellpadding='4'><thead><tr>"
            "<th>Key</th><th>Value</th></tr></thead><tbody>%s</tbody></table>"
            % "".join(rows)
        )
        return (
            "<!DOCTYPE html><html><head><meta charset='utf-8'>"
            "</head><body>%s</body></html>" % body
        )
