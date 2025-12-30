from typing import cast

from PyQt5.QtCore import (
    QModelIndex,
    QRect,
    QSize,
    Qt,
)
from PyQt5.QtGui import QFont, QIcon, QPainter, QTextDocument
from PyQt5.QtWidgets import (
    QListView,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QWidget,
)

from exdrf_qt.controls.command_palette.constants import (
    ICON_ROLE,
    ICON_SIZE,
    MAX_POPUP_WIDTH,
    PADDING,
    SPACING_BETWEEN_TITLE_AND_SUBTITLE,
    SUBTITLE_FONT_FACTOR,
    SUBTITLE_ROLE,
    TITLE_FONT_FACTOR,
    TITLE_ROLE,
)


class CompleterItemDelegate(QStyledItemDelegate):
    """Custom delegate for completer items with icon and double text."""

    def __init__(self, parent: "QWidget"):
        """Initialize the delegate."""
        super().__init__(parent)
        self._icon = QIcon()

    def paint(
        self,
        painter: "QPainter",
        option: "QStyleOptionViewItem",
        index: "QModelIndex",
    ) -> None:
        """Paint the item with icon, title, and subtitle."""
        # Get data from the model
        title = index.data(TITLE_ROLE)
        subtitle = index.data(SUBTITLE_ROLE)
        icon = index.data(ICON_ROLE)

        if not title:
            return

        # From QCompleterItemDelegate.
        option.showDecorationSelected = True
        view: "QListView" = cast(QListView, self.parent())
        if view.currentIndex() == index:
            option.state |= QStyle.StateFlag.State_HasFocus

        # Setup painter
        painter.save()

        # Draw selection/hover background
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(option.rect, option.palette.midlight())

        # Icon size and padding
        icon_size = ICON_SIZE
        padding = PADDING
        icon_y = option.rect.top() + (option.rect.height() - icon_size) // 2
        icon_rect = QRect(
            option.rect.left() + padding,
            icon_y,
            icon_size,
            icon_size,
        )

        # Draw icon from model
        if icon and isinstance(icon, QIcon) and not icon.isNull():
            icon.paint(painter, icon_rect, Qt.AlignmentFlag.AlignCenter)

        # Text area (to the right of icon)
        text_x = icon_rect.right() + padding
        text_width = option.rect.width() - text_x - padding
        text_rect = QRect(
            text_x, option.rect.top(), text_width, option.rect.height()
        )

        # Calculate fonts
        bold_font = QFont(option.font)
        bold_font.setPointSize(int(option.font.pointSize() * TITLE_FONT_FACTOR))
        bold_font.setBold(True)

        small_font = QFont(option.font)
        small_font.setPointSize(
            int(option.font.pointSize() * SUBTITLE_FONT_FACTOR)
        )

        # Calculate wrapped text heights using QTextDocument
        spacing = SPACING_BETWEEN_TITLE_AND_SUBTITLE

        # Calculate title height (wrapped)
        title_doc = QTextDocument()
        title_doc.setDefaultFont(bold_font)
        title_doc.setTextWidth(text_width)
        title_doc.setPlainText(title)
        title_height = int(title_doc.size().height())

        # Calculate subtitle height (wrapped)
        subtitle_height = 0
        subtitle_doc = None
        if subtitle:
            subtitle_doc = QTextDocument()
            subtitle_doc.setDefaultFont(small_font)
            subtitle_doc.setTextWidth(text_width)
            subtitle_doc.setPlainText(subtitle)
            subtitle_height = int(subtitle_doc.size().height())

        # Start drawing from top with padding
        start_y = text_rect.top() + padding

        # Draw title (bold, wrapped)
        painter.setFont(bold_font)
        painter.setPen(option.palette.text().color())
        title_rect = QRect(text_rect.left(), start_y, text_width, title_height)
        painter.save()
        painter.translate(title_rect.topLeft())
        title_doc.drawContents(painter)
        painter.restore()

        # Draw subtitle (small, wrapped)
        if subtitle_doc and subtitle_height > 0:
            painter.setFont(small_font)
            painter.setPen(option.palette.mid().color())
            subtitle_y = start_y + title_height + spacing
            subtitle_rect = QRect(
                text_rect.left(), subtitle_y, text_width, subtitle_height
            )
            painter.save()
            painter.translate(subtitle_rect.topLeft())
            subtitle_doc.drawContents(painter)
            painter.restore()

        painter.restore()

    def sizeHint(
        self, option: "QStyleOptionViewItem", index: "QModelIndex"
    ) -> "QSize":
        """Return the size hint for the item."""
        title = index.data(TITLE_ROLE)
        subtitle = index.data(SUBTITLE_ROLE)
        if not title:
            return super().sizeHint(option, index)

        # Icon size and padding
        icon_size = ICON_SIZE
        padding = PADDING

        # Calculate available text width (accounting for max width)
        icon_and_padding_width = icon_size + padding * 3
        max_text_width = MAX_POPUP_WIDTH - icon_and_padding_width
        # Account for scrollbar if needed
        scrollbar_width = 0
        if option.widget:
            style = option.widget.style()
            if style:
                scrollbar_width = style.pixelMetric(
                    QStyle.PixelMetric.PM_ScrollBarExtent
                )
        max_text_width -= scrollbar_width

        # Calculate fonts
        bold_font = QFont(option.font)
        bold_font.setPointSize(int(option.font.pointSize() * TITLE_FONT_FACTOR))
        bold_font.setBold(True)

        small_font = QFont(option.font)
        small_font.setPointSize(
            int(option.font.pointSize() * SUBTITLE_FONT_FACTOR)
        )

        # Calculate wrapped text heights using QTextDocument
        # Calculate title height (wrapped)
        title_doc = QTextDocument()
        title_doc.setDefaultFont(bold_font)
        title_doc.setTextWidth(max_text_width)
        title_doc.setPlainText(title)
        title_height = int(title_doc.size().height())

        # Calculate subtitle height (wrapped)
        subtitle_height = 0
        if subtitle:
            subtitle_doc = QTextDocument()
            subtitle_doc.setDefaultFont(small_font)
            subtitle_doc.setTextWidth(max_text_width)
            subtitle_doc.setPlainText(subtitle)
            subtitle_height = int(subtitle_doc.size().height())

        # Calculate total height
        spacing = SPACING_BETWEEN_TITLE_AND_SUBTITLE
        total_text_height = title_height + subtitle_height
        if subtitle:
            total_text_height += spacing

        total_height = max(icon_size, total_text_height) + padding * 2
        total_width = min(
            icon_and_padding_width + max_text_width + scrollbar_width,
            MAX_POPUP_WIDTH,
        )

        return QSize(total_width, total_height)
