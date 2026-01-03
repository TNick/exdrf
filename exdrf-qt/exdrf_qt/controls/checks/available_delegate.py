"""Item delegate for displaying checks with a two-line layout."""

from __future__ import annotations

import html

from PyQt5.QtCore import QModelIndex, QPoint, QRect, QSize, Qt
from PyQt5.QtGui import (
    QAbstractTextDocumentLayout,
    QIcon,
    QPainter,
    QPalette,
    QTextDocument,
)
from PyQt5.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem


class AvailableChecksDelegate(QStyledItemDelegate):
    """Delegate that draws a bold title and an italic description.

    The icon is drawn to the left, and the text is rendered using a
    ``QTextDocument`` so word wrapping and variable height are supported.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        if index.column() != 0:
            return super().paint(painter, option, index)

        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)

        # Capture the decoration icon before we clear it from the style option.
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        if not isinstance(icon, QIcon):
            icon = QIcon()

        # Let the style draw the selection/background, but not decoration/text.
        text = opt.text
        opt.text = ""
        opt.icon = QIcon()
        opt.features &= ~QStyleOptionViewItem.HasDecoration
        opt.features &= ~QStyleOptionViewItem.HasDisplay
        style = opt.widget.style() if opt.widget is not None else None
        if style is None:
            return super().paint(painter, option, index)

        painter.save()
        style.drawControl(
            QStyle.ControlElement.CE_ItemViewItem,
            opt,
            painter,
            opt.widget,
        )

        # Prepare title + description.
        title = text or ""
        desc = index.data(Qt.ItemDataRole.UserRole + 1) or ""

        # Compute rectangles.
        icon_size = opt.decorationSize
        if icon_size.isEmpty():
            icon_size = QSize(16, 16)

        padding = 6

        # Center the icon vertically within the row.
        icon_y = opt.rect.top() + (opt.rect.height() - icon_size.height()) // 2
        icon_rect = QRect(
            opt.rect.left() + padding,
            icon_y,
            icon_size.width(),
            icon_size.height(),
        )
        text_left = icon_rect.right() + padding
        text_rect = QRect(
            text_left,
            opt.rect.top() + padding,
            opt.rect.right() - text_left - padding,
            opt.rect.height() - 2 * padding,
        )

        # Draw icon.
        if not icon.isNull():
            icon.paint(painter, icon_rect, Qt.AlignmentFlag.AlignCenter)

        # Draw rich text.
        doc = self._create_doc(
            title=title,
            description=desc,
            font=opt.font,
            text_width=max(10, text_rect.width()),
        )

        painter.translate(text_rect.topLeft())
        painter.setClipRect(QRect(QPoint(0, 0), text_rect.size()))

        # Create a proper paint context (PyQt expects this, not a QPalette).
        ctx = QAbstractTextDocumentLayout.PaintContext()
        ctx.palette = opt.palette

        # Ensure readable text when selected.
        if opt.state & QStyle.StateFlag.State_Selected:
            ctx.palette.setColor(
                QPalette.ColorRole.Text,
                opt.palette.color(
                    QPalette.ColorGroup.Active,
                    QPalette.ColorRole.HighlightedText,
                ),
            )

        layout = doc.documentLayout()
        if layout is not None:
            layout.draw(painter, ctx)

        painter.restore()

    def sizeHint(
        self, option: QStyleOptionViewItem, index: QModelIndex
    ) -> QSize:
        if index.column() != 0:
            return super().sizeHint(option, index)

        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)

        title = opt.text or ""
        desc = index.data(Qt.ItemDataRole.UserRole + 1) or ""

        icon_size = opt.decorationSize
        if icon_size.isEmpty():
            icon_size = QSize(16, 16)

        padding = 6
        if opt.rect.width() > 0:
            width = opt.rect.width()
        elif opt.widget is not None and opt.widget.viewport() is not None:
            width = opt.widget.viewport().width()
        else:
            width = 240
        text_width = max(10, width - icon_size.width() - 3 * padding)

        doc = self._create_doc(
            title=title,
            description=desc,
            font=opt.font,
            text_width=text_width,
        )

        doc_h = int(doc.size().height())
        icon_h = icon_size.height()
        height = max(icon_h, doc_h) + 2 * padding
        return QSize(width, height)

    def _create_doc(
        self,
        title: str,
        description: str,
        font,
        text_width: int,
    ) -> QTextDocument:
        """Create a QTextDocument for the two-line check display.

        Args:
            title: The title text.
            description: The description text (may contain newlines).
            font: Base font from the style option.
            text_width: Layout width in pixels.

        Returns:
            Configured QTextDocument.
        """
        doc = QTextDocument()
        doc.setDefaultFont(font)

        # Remove default margins to avoid extra empty space.
        doc.setDocumentMargin(0)

        safe_title = html.escape(title)

        # Preserve newlines in the description.
        safe_desc = html.escape(description).replace("\n", "<br/>")

        if safe_desc:
            html_text = (
                "<p style='margin:0;'>"
                f"<b>{safe_title}</b><br/>"
                f"<span style='font-style:italic;'>{safe_desc}</span>"
                "</p>"
            )
        else:
            html_text = f"<p style='margin:0;'><b>{safe_title}</b></p>"

        doc.setHtml(html_text)
        doc.setTextWidth(text_width)
        return doc
