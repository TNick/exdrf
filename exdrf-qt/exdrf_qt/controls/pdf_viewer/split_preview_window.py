"""Floating window that previews the pages of a split entry."""

from typing import TYPE_CHECKING, Callable, Dict, List, Optional, cast

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QTransform
from PyQt5.QtWidgets import (
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from exdrf_qt.controls.pdf_viewer.pdf_image_viewer import PdfImageViewer


class SplitPreviewWindow(QWidget):
    """Floating window that previews the pages of a split entry."""

    def __init__(
        self,
        viewer: "PdfImageViewer",
        pages: List[int],
        rotations: Optional[Dict[int, int]],
        title: str,
        translator: Callable[..., str],
    ):
        """Create a floating window populated with preview placeholders."""
        super().__init__(viewer)
        self._viewer = viewer
        self._pages = sorted({page for page in pages if page >= 1})
        self._rotations = rotations or {}
        self._translator = translator
        self._page_labels: Dict[int, QLabel] = {}

        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowFlag(Qt.WindowType.Window, True)

        # Configure the window caption using the entry title.
        resolved_title = title.strip() if title else ""
        if not resolved_title:
            resolved_title = self._translator(
                "pdf.split.preview.untitled", "Split entry"
            )
        self.setWindowTitle(
            self._translator(
                "pdf.split.preview.title",
                "Preview: {title}",
                title=resolved_title,
            )
        )
        self.resize(720, 840)

        # Show a short textual summary of the selected pages.
        summary_label = QLabel(
            self._translator(
                "pdf.split.preview.summary",
                "Showing pages: {pages}",
                pages=", ".join(str(page) for page in self._pages) or "—",
            )
        )
        summary_label.setWordWrap(True)

        # Status label surfaces pending renders to the user.
        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        self._status_label.setVisible(False)

        # Scroll area helps when many thumbnails are listed simultaneously.
        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        container = QWidget()
        self._pages_layout = QVBoxLayout()
        self._pages_layout.setContentsMargins(8, 8, 8, 8)
        self._pages_layout.setSpacing(12)
        pages_alignment = cast(
            Qt.AlignmentFlag,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
        )
        self._pages_layout.setAlignment(pages_alignment)
        container.setLayout(self._pages_layout)
        self._scroll.setWidget(container)

        layout = QVBoxLayout()
        layout.addWidget(summary_label)
        layout.addWidget(self._scroll, 1)
        layout.addWidget(self._status_label)
        self.setLayout(layout)

        # Seed the layout with placeholders for each requested page.
        for page in self._pages:
            label = QLabel(
                self._translator(
                    "pdf.split.preview.loading",
                    "Rendering page {page}…",
                    page=page,
                )
            )
            label.setAlignment(
                cast(Qt.AlignmentFlag, Qt.AlignmentFlag.AlignCenter)
            )
            label.setMinimumHeight(120)
            label.setSizePolicy(
                QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            )
            self._pages_layout.addWidget(label)
            self._page_labels[page] = label
        self._pages_layout.addStretch(1)

        # Keep the preview synchronized with the live viewer.
        self._viewer.pageImageReady.connect(self._handle_page_ready)
        self._viewer.destroyed.connect(self._handle_viewer_deleted)
        self.destroyed.connect(self._disconnect_signals)

        if self._pages:
            self._viewer.prefetch_pages(self._pages)
        self._refresh_all_pages()

    def _handle_viewer_deleted(self, *_):
        """Close preview when the owning viewer is destroyed."""
        try:
            self.close()
        except RuntimeError:
            pass

    def _handle_page_ready(self, page_number: int):
        """Update the preview when a requested page becomes available."""
        if page_number not in self._pages:
            return
        updated = self._update_label(page_number)
        if updated:
            self._update_status_label()

    def _refresh_all_pages(self):
        """Populate labels with any already-rendered pixmaps."""
        for page in self._pages:
            self._update_label(page)
        self._update_status_label()

    def _update_label(self, page: int) -> bool:
        """Set the pixmap for a specific page label when available."""
        label = self._page_labels.get(page)
        if label is None:
            return False
        pixmap = self._viewer.get_cached_pixmap(page)
        if pixmap is None:
            label.setPixmap(QPixmap())
            label.setText(
                self._translator(
                    "pdf.split.preview.loading",
                    "Rendering page {page}…",
                    page=page,
                )
            )
            return False

        rotation = self._rotations.get(page, 0) % 360
        display_pix = pixmap
        if rotation:
            transform = QTransform()
            transform.rotate(rotation)
            display_pix = pixmap.transformed(
                transform, Qt.TransformationMode.SmoothTransformation
            )

        label.setText("")
        label.setPixmap(display_pix)
        label.setMinimumSize(display_pix.size())
        label.setSizePolicy(
            QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        )
        return True

    def _update_status_label(self):
        """Display status text for pages still rendering."""
        pending = [
            page
            for page in self._pages
            if self._viewer.get_cached_pixmap(page) is None
        ]
        if pending:
            self._status_label.setText(
                self._translator(
                    "pdf.split.preview.pending",
                    "Waiting for pages: {pages}",
                    pages=", ".join(str(page) for page in pending),
                )
            )
            self._status_label.setVisible(True)
        else:
            self._status_label.clear()
            self._status_label.setVisible(False)

    def _disconnect_signals(self, *_):
        """Safely disconnect Qt signals."""
        try:
            self._viewer.pageImageReady.disconnect(self._handle_page_ready)
        except (RuntimeError, TypeError):
            pass
        try:
            self._viewer.destroyed.disconnect(self._handle_viewer_deleted)
        except (RuntimeError, TypeError):
            pass
