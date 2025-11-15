import logging
from typing import Optional, TYPE_CHECKING

from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtGui import QBrush, QColor, QPainter, QPixmap
from PyQt5.QtWidgets import QGraphicsView

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget  # noqa: F401

logger = logging.getLogger(__name__)


class ImageGraphicsView(QGraphicsView):
    """Graphics view with wheel zoom and middle mouse panning.

    Provides a graphics view widget with enhanced interaction capabilities:
    - Mouse wheel zooms in/out around the cursor position
    - Middle mouse button enables panning
    - Checkerboard background pattern for better visibility
    - Configurable zoom limits

    Attributes:
        _middle_panning: Whether middle mouse button panning is active.
        _last_mouse_pos: Last mouse position during panning.
        _zoom: Current zoom level (1.0 = 100%).
        _zoom_min: Minimum allowed zoom level.
        _zoom_max: Maximum allowed zoom level.
    """

    def __init__(self, parent: Optional["QWidget"] = None):
        """Initialize the graphics view.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setRenderHints(self.renderHints())
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.NoDrag)
        self._middle_panning = False
        self._last_mouse_pos = QPoint()
        self._zoom = 1.0
        self._zoom_min = 0.05
        self._zoom_max = 16.0

        # Smooth scrolling and anti-aliasing feel better with these flags
        self.setViewportUpdateMode(QGraphicsView.SmartViewportUpdate)

        # Distinctive checkerboard background for the view
        self.setBackgroundBrush(QBrush(self._make_checkerboard_pixmap()))

    def _make_checkerboard_pixmap(
        self,
        cell: int = 8,
        c1: Optional[QColor] = None,
        c2: Optional[QColor] = None,
    ) -> QPixmap:
        """Create a checkerboard pattern pixmap for the background.

        Args:
            cell: Size of each checkerboard cell in pixels.
            c1: Primary color (light gray by default).
            c2: Secondary color (darker gray by default).

        Returns:
            A tiled checkerboard pattern pixmap.
        """
        if c1 is None:
            c1 = QColor(230, 230, 230)
        if c2 is None:
            c2 = QColor(200, 200, 200)
        size = cell * 2
        pix = QPixmap(size, size)
        pix.fill(c1)
        p = QPainter(pix)
        try:
            p.fillRect(0, 0, cell, cell, c2)
            p.fillRect(cell, cell, cell, cell, c2)
        finally:
            p.end()
        return pix

    def set_zoom(self, zoom: float):
        """Set the zoom level.

        Args:
            zoom: Desired zoom level (clamped to min/max limits).
        """
        if zoom <= 0:
            return
        zoom = max(self._zoom_min, min(self._zoom_max, zoom))
        factor = zoom / self._zoom
        self.scale(factor, factor)
        self._zoom = zoom

    def zoom_in(self, step: float = 1.25):
        """Zoom in by the specified step factor.

        Args:
            step: Zoom multiplier (default 1.25 = 25% increase).
        """
        self.set_zoom(self._zoom * step)

    def zoom_out(self, step: float = 1.25):
        """Zoom out by the specified step factor.

        Args:
            step: Zoom divisor (default 1.25 = 20% decrease).
        """
        self.set_zoom(self._zoom / step)

    def reset_zoom(self, zoom: float = 1.0):
        """Reset zoom to 1.0 and then set to the specified level.

        Args:
            zoom: Target zoom level after reset (default 1.0).
        """
        if self._zoom == 0:
            return
        self.scale(1.0 / self._zoom, 1.0 / self._zoom)
        self._zoom = 1.0
        self.set_zoom(zoom)

    def wheelEvent(self, event):
        """Handle mouse wheel events for zooming.

        Args:
            event: The wheel event.
        """
        if event is None:
            return
        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom_in()
        elif delta < 0:
            self.zoom_out()
        event.accept()

    def mousePressEvent(self, event):
        """Handle mouse press events for middle-button panning.

        Args:
            event: The mouse event.
        """
        if event is None:
            return
        if event.button() == Qt.MouseButton.MiddleButton:
            self._middle_panning = True
            self._last_mouse_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move events for panning.

        Args:
            event: The mouse event.
        """
        if event is None:
            return
        if self._middle_panning:
            delta = event.pos() - self._last_mouse_pos
            self._last_mouse_pos = event.pos()
            hbar = self.horizontalScrollBar()
            vbar = self.verticalScrollBar()
            if hbar is not None:
                hbar.setValue(hbar.value() - delta.x())
            if vbar is not None:
                vbar.setValue(vbar.value() - delta.y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release events to stop panning.

        Args:
            event: The mouse event.
        """
        if event is None:
            return
        if (
            event.button() == Qt.MouseButton.MiddleButton
            and self._middle_panning
        ):
            self._middle_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)
