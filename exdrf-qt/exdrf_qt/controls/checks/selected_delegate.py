"""Delegate for rendering selected checks with progress bars."""

from __future__ import annotations

from typing import Any, Dict

from PyQt5.QtCore import QModelIndex, QSize, Qt
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import (
    QStyle,
    QStyledItemDelegate,
    QStyleOptionProgressBar,
    QStyleOptionViewItem,
)

from exdrf_qt.controls.checks.available_delegate import AvailableChecksDelegate
from exdrf_qt.controls.checks.selected_model import PROGRESS_ROLE


class SelectedChecksDelegate(QStyledItemDelegate):
    """Delegate that renders selected checks with progress bars.

    Attributes:
        _text_delegate: Delegate used for the first column text rendering.
    """

    _text_delegate: AvailableChecksDelegate

    def __init__(self, parent=None) -> None:
        """Create the delegate.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._text_delegate = AvailableChecksDelegate(parent)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        """Paint the requested cell.

        Args:
            painter: Target painter.
            option: Style option for the cell.
            index: Model index being painted.
        """
        if index.column() == 0:
            self._text_delegate.paint(painter, option, index)
            return

        payload = index.data(PROGRESS_ROLE)
        if not isinstance(payload, dict):
            super().paint(painter, option, index)
            return

        bar_opt = self._build_progress_option(option, payload)
        style = option.widget.style() if option.widget is not None else None
        if style is None:
            super().paint(painter, option, index)
            return

        # Draw the progress bar using the widget style for consistency.
        style.drawControl(
            QStyle.ControlElement.CE_ProgressBar,
            bar_opt,
            painter,
            option.widget,
        )

    def sizeHint(
        self, option: QStyleOptionViewItem, index: QModelIndex
    ) -> QSize:
        """Return a size hint that matches the text column height.

        Args:
            option: Style option for the cell.
            index: Model index being measured.

        Returns:
            Suggested size for the cell.
        """
        if index.column() == 0:
            return self._text_delegate.sizeHint(option, index)

        sibling = index.sibling(index.row(), 0)
        return self._text_delegate.sizeHint(option, sibling)

    def _build_progress_option(
        self,
        option: QStyleOptionViewItem,
        payload: Dict[str, Any],
    ) -> QStyleOptionProgressBar:
        """Create a ``QStyleOptionProgressBar`` from the model payload.

        Args:
            option: Base style option received in ``paint``.
            payload: Mapping containing progress data.

        Returns:
            Configured progress bar style option.
        """
        bar_opt = QStyleOptionProgressBar()

        # Mirror the view option so selection/hover state stay in sync.
        bar_opt.rect = option.rect
        bar_opt.state = option.state
        bar_opt.direction = option.direction
        bar_opt.fontMetrics = option.fontMetrics
        bar_opt.palette = option.palette

        # Configure text and alignment.
        bar_opt.textVisible = True
        bar_opt.textAlignment = Qt.AlignmentFlag.AlignCenter
        bar_opt.text = str(payload.get("text", ""))

        # Configure range and progress value.
        is_indeterminate = bool(payload.get("indeterminate"))
        is_failed = bool(payload.get("failed"))
        bar_opt.minimum = 0
        bar_opt.maximum = 0 if is_indeterminate else 100

        progress_val = int(payload.get("value", 0))
        progress_val = max(0, min(100, progress_val))
        if is_failed:
            progress_val = 100
        bar_opt.progress = progress_val

        return bar_opt
