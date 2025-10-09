import logging
import weakref
from typing import Optional, cast

from PyQt5.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPoint,
    QPropertyAnimation,
    Qt,
    QTimer,
)
from PyQt5.QtGui import QFont, QMouseEvent
from PyQt5.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class Toast(QWidget):
    """Toast message with fade animations and a progress bar.

    Messages are grouped and stacked per parent in an on-top container.
    Each message shows a countdown progress bar, pauses on hover and can be
    closed via a small close button. Use the convenience methods to add
    messages: ``show_info``, ``show_warning``, ``show_error``.

    Attributes:
        _label: Message label.
        _progress: Per-message progress bar.
        _duration_ms: Duration before auto-close.
        _fade_ms: Fade animation duration.
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
        self._remaining_ms = self._duration_ms
        self._kind = (kind or "info").lower()

        # Layout: outer + card (with padding), then content row + progress bar
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._card = QWidget(self)
        self._card.setObjectName("ToastCard")
        outer.addWidget(self._card)

        layout = QVBoxLayout(self._card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(0)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

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

        # Close button
        self._close_btn = QPushButton("✕", self)
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.setFlat(True)
        self._close_btn.setFixedSize(20, 20)
        self._close_btn.clicked.connect(self._start_fade_out)  # type: ignore

        # Place widgets
        row.addWidget(self._label, 1)
        row.addWidget(self._close_btn, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(row)

        # Progress bar
        self._progress = QProgressBar(self)
        self._progress.setTextVisible(False)
        self._progress.setMaximum(1000)
        self._progress.setValue(0)
        self._progress.setFixedHeight(5)
        layout.addWidget(self._progress)

        # Width constraints
        self._card.setMinimumWidth(220)
        self._card.setMaximumWidth(420)

        # Apply style by kind
        self._apply_style(self._kind)

        # Opacity effect
        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity)

        # Animations
        self._anim = QPropertyAnimation(self._opacity, b"opacity", self)
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)
        self._anim.setDuration(self._fade_ms)

        # Tick timer for progress/timeout
        self._tick_ms = 30
        self._tick = QTimer(self)
        self._tick.setSingleShot(False)
        self._tick.timeout.connect(self._on_tick)

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
        # Route to per-parent container so messages stack
        container = _get_container(parent)
        return container.add_message(
            message, kind=kind, duration_ms=duration_ms
        )

    # ----------------------------
    # Internals
    # ----------------------------
    def _present(self) -> None:
        # Show and fade in
        self.show()
        self._anim.stop()
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

        # Start countdown
        if self._duration_ms > 0:
            self._remaining_ms = self._duration_ms
            self._progress.setValue(0)
            self._tick.start(self._tick_ms)

    def _start_fade_out(self) -> None:
        # Stop timers and fade out then close
        if self._tick.isActive():
            self._tick.stop()
        self._anim.stop()
        self._anim.setStartValue(self._opacity.opacity())
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(self.close)  # type: ignore
        self._anim.start()

    def _on_tick(self) -> None:
        # Update remaining time and progress; auto-close when done
        self._remaining_ms = max(0, self._remaining_ms - self._tick_ms)
        if self._duration_ms <= 0:
            self._progress.setValue(0)
            return
        value = int(
            (self._duration_ms - self._remaining_ms)
            * 1000
            / max(1, self._duration_ms)
        )
        self._progress.setValue(min(1000, max(0, value)))
        if self._remaining_ms == 0:
            self._start_fade_out()

    def _apply_style(self, kind: str) -> None:
        kind_key = (kind or "info").lower()

        # Color palette per kind
        if kind_key == "error":
            bg = "#fcebea"
            border = "#f5c6cb"
            text = "#721c24"
            icon = "❌"
            bar = "#e99a9a"
        elif kind_key == "warning":
            bg = "#fff3cd"
            border = "#ffeeba"
            text = "#856404"
            icon = "⚠"
            bar = "#e7d38a"
        else:
            bg = "#d1ecf1"
            border = "#bee5eb"
            text = "#0c5460"
            icon = "ℹ"
            bar = "#9fd3dc"

        # Label with icon
        self._label.setText(f"{icon}  {self._label.text()}")

        # Style card widget and progress bar
        self._card.setStyleSheet(
            """
            QWidget#ToastCard {
                color: %s;
                background: %s;
                border: 1px solid %s;
                border-radius: 6px;
            }
            QProgressBar {
                background: transparent;
                border: none;
                height: 5px;
            }
            QProgressBar::chunk {
                background-color: %s;
                border-radius: 2px;
            }
            """
            % (text, bg, border, bar)
        )
        # Ensure the card paints its background
        self._card.setAutoFillBackground(True)

    def mouseReleaseEvent(self, a0: Optional[QMouseEvent]) -> None:
        self._start_fade_out()

    def enterEvent(self, a0: Optional[QEvent]) -> None:
        # Pause countdown on hover
        if self._tick.isActive():
            self._tick.stop()

    def leaveEvent(self, a0: Optional[QEvent]) -> None:
        # Resume countdown when leaving
        if self._duration_ms > 0 and not self._tick.isActive():
            self._tick.start(self._tick_ms)


# ----------------------------
# Container for per-parent stacks
# ----------------------------
class _ToastContainer(QWidget):
    """On-top container that stacks toast messages for a given parent."""

    def __init__(self, owner: Optional[QWidget]) -> None:
        super().__init__(owner)

        # Window flags for floating, translucent container
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

        # Layout for stacked toasts
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)

        # Track owner to reposition on changes
        self._owner_ref = weakref.ref(owner) if owner is not None else None
        if owner is not None:
            owner.installEventFilter(self)

    # ----------------------------
    # Public API
    # ----------------------------
    def add_message(
        self, message: str, *, kind: str, duration_ms: int
    ) -> Toast:
        toast = Toast(self, message, kind=kind, duration_ms=duration_ms)
        self._layout.addWidget(toast, 0, Qt.AlignmentFlag.AlignRight)
        toast._present()
        self._reposition()
        self.show()
        toast.destroyed.connect(self._on_item_destroyed)
        return toast

    # ----------------------------
    # Internals
    # ----------------------------
    def _on_item_destroyed(self, *args: object) -> None:
        # Remove empty space and hide when no children left
        self._cleanup_gone_widgets()
        if self._layout.count() == 0:
            self.hide()
        self._reposition()

    def _cleanup_gone_widgets(self) -> None:
        # Remove any deleted placeholders
        for i in reversed(range(self._layout.count())):
            item = self._layout.itemAt(i)
            w = item.widget() if item is not None else None
            if w is None or w.isHidden():
                self._layout.takeAt(i)

    def _reposition(self) -> None:
        # Size to content
        self.adjustSize()

        owner = self._owner_ref() if self._owner_ref is not None else None
        if owner is None:
            # Position to screen top-right
            screen = self.screen()
            if screen is None:
                return
            screen_geo = screen.availableGeometry()
            x = screen_geo.right() - self.width() - 24
            y = screen_geo.top() + 24
            self.move(QPoint(max(0, x), max(0, y)))
            return

        try:
            pr = owner.rect()
            gp = owner.mapToGlobal(pr.topLeft())
            x = gp.x() + pr.width() - self.width() - 24
            y = gp.y() + 24
            self.move(QPoint(x, y))
        except Exception as e:
            logger.debug("Toast container position fallback: %s", e)

    def eventFilter(
        self, a0: Optional[QObject], a1: Optional[QEvent]
    ) -> bool:  # type: ignore[override]
        # Reposition container when owner moves/resizes/shows
        if a1 is not None:
            et = a1.type()
        else:
            et = QEvent.Type.None_
        if et in (
            QEvent.Type.Resize,
            QEvent.Type.Move,
            QEvent.Type.Show,
            QEvent.Type.WindowStateChange,
        ):
            self._reposition()
        return super().eventFilter(a0, a1)


# ----------------------------
# Container management
# ----------------------------
_containers: "weakref.WeakKeyDictionary[QWidget, _ToastContainer]" = (
    weakref.WeakKeyDictionary()
)
_root_container: Optional[_ToastContainer] = None


def _get_container(parent: Optional[QWidget]) -> _ToastContainer:
    global _root_container
    if parent is None:
        if _root_container is None:
            _root_container = _ToastContainer(None)
        return _root_container

    container = _containers.get(parent)
    if container is None:
        container = _ToastContainer(parent)
        _containers[parent] = container
    return container
