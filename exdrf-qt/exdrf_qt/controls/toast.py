import logging
from typing import Optional, cast

from PyQt5.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt, QTimer
from PyQt5.QtGui import QFont, QMouseEvent
from PyQt5.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget

logger = logging.getLogger(__name__)


class Toast(QWidget):
    """Transient toast-style message with fade in/out animations.

    The widget is frame-less and always-on-top relative to the given parent.
    It positions itself near the bottom-right corner of the parent and
    auto-closes after a short duration. Use the convenience class methods
    for different severities: ``show_info``, ``show_warning``, ``show_error``.

    Attributes:
        _label: Inner ``QLabel`` displaying the message text.
        _duration_ms: Time in milliseconds before starting fade-out.
        _fade_ms: Animation duration in milliseconds for fade-in/out.
    """

    _DEFAULT_DURATION_MS = 6000
    _DEFAULT_FADE_MS = 500

    def __init__(
        self,
        parent: Optional[QWidget],
        message: str,
        *,
        kind: str = "info",
        duration_ms: int = _DEFAULT_DURATION_MS,
        fade_ms: int = _DEFAULT_FADE_MS,
    ) -> None:
        super().__init__(parent)

        # Store parameters
        self._duration_ms = max(0, duration_ms)
        self._fade_ms = max(60, fade_ms)

        # Basic window flags for a toast look
        self.setWindowFlags(
            cast(
                Qt.WindowFlags,
                Qt.WindowType.ToolTip
                | Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.NoDropShadowWindowHint,
            )
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        # Content label
        self._label = QLabel(self)
        self._label.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        self._label.setWordWrap(True)
        self._label.setText(message)
        self._label.setAlignment(
            cast(
                Qt.AlignmentFlag,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            )
        )

        # Font slightly larger than default
        f = QFont(self._label.font())
        f.setPointSize(max(9, f.pointSize() + 1))
        self._label.setFont(f)

        # Apply style by kind
        self._apply_style(kind)

        # Padding and width constraints
        self._label.setMargin(12)
        self._label.setMinimumWidth(220)
        self._label.setMaximumWidth(420)

        # Set size to label's size
        self._label.adjustSize()
        self.resize(self._label.size())

        # Opacity effect
        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity)

        # Animations
        self._anim = QPropertyAnimation(self._opacity, b"opacity", self)
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)
        self._anim.setDuration(self._fade_ms)

        # Auto-close timer
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._start_fade_out)

    # ----------------------------
    # Public API
    # ----------------------------
    @classmethod
    def show_info(
        cls,
        parent: Optional[QWidget],
        message: str,
        *,
        duration_ms: int = _DEFAULT_DURATION_MS,
    ) -> "Toast":
        return cls._show(parent, message, kind="info", duration_ms=duration_ms)

    @classmethod
    def show_warning(
        cls,
        parent: Optional[QWidget],
        message: str,
        *,
        duration_ms: int = _DEFAULT_DURATION_MS,
    ) -> "Toast":
        return cls._show(
            parent,
            message,
            kind="warning",
            duration_ms=duration_ms,
        )

    @classmethod
    def show_error(
        cls,
        parent: Optional[QWidget],
        message: str,
        *,
        duration_ms: int = _DEFAULT_DURATION_MS,
    ) -> "Toast":
        return cls._show(parent, message, kind="error", duration_ms=duration_ms)

    @classmethod
    def _show(
        cls,
        parent: Optional[QWidget],
        message: str,
        *,
        kind: str,
        duration_ms: int,
    ) -> "Toast":
        toast = cls(parent, message, kind=kind, duration_ms=duration_ms)
        toast._present()
        return toast

    # ----------------------------
    # Internals
    # ----------------------------
    def _present(self) -> None:
        # Compute position relative to parent
        parent = self.parentWidget()
        if parent is None:
            screen = self.screen()
            assert screen is not None
            screen_geo = screen.availableGeometry()
            x = screen_geo.right() - self.width() - 24
            y = screen_geo.bottom() - self.height() - 24
            self.move(QPoint(max(0, x), max(0, y)))
        else:
            try:
                pr = parent.rect()
                gp = parent.mapToGlobal(pr.topLeft())
                x = gp.x() + pr.width() - self.width() - 24
                y = gp.y() + 24
                self.move(QPoint(x, y))
            except Exception as e:
                logger.debug("Toast position fallback: %s", e)

        # Show and fade in
        self.show()
        self._anim.stop()
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

        # Start timer for fade-out
        if self._duration_ms > 0:
            self._timer.start(self._duration_ms)

    def _start_fade_out(self) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._opacity.opacity())
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(self.close)  # type: ignore
        self._anim.start()

    def _apply_style(self, kind: str) -> None:
        kind_key = (kind or "info").lower()

        # Color palette per kind
        if kind_key == "error":
            bg = "#fcebea"  # light red-ish
            border = "#f5c6cb"
            text = "#721c24"
            icon = "❌"
        elif kind_key == "warning":
            bg = "#fff3cd"  # light yellow
            border = "#ffeeba"
            text = "#856404"
            icon = "⚠"
        else:
            bg = "#d1ecf1"  # light blue
            border = "#bee5eb"
            text = "#0c5460"
            icon = "ℹ"

        self._label.setText(f"{icon}  {self._label.text()}")
        self._label.setStyleSheet(
            """
            QLabel {
                color: %s;
                background: %s;
                border: 1px solid %s;
                border-radius: 6px;
            }
            """
            % (text, bg, border)
        )

    def mouseReleaseEvent(self, a0: Optional[QMouseEvent]) -> None:
        self._start_fade_out()
