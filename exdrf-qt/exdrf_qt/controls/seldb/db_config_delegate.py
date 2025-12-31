from typing import TYPE_CHECKING
from urllib.parse import urlparse

from PyQt5.QtCore import QRect, QSize, Qt
from PyQt5.QtGui import QFont, QFontMetrics, QPainter
from PyQt5.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.seldb.utils import (
    CON_TYPE_LOCAL,
    CON_TYPE_REMOTE,
)

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401


class DbConfigDelegate(QStyledItemDelegate, QtUseContext):
    """A delegate for rendering database connection configurations.

    Displays each config with:
    - An icon (document_empty for local, globe_africa for remote)
    - Name and type in bold, larger font
    - Connection details (host, port, database, user, schema) below

    Attributes:
        ctx: The Qt context.
    """

    ctx: "QtContext"

    def __init__(self, ctx: "QtContext", parent=None):
        """Initialize the delegate.

        Args:
            ctx: The Qt context.
            parent: Optional parent object.
        """
        super().__init__(parent)
        self.ctx = ctx

    def sizeHint(self, option, index):
        """Return the size hint for the item.

        Args:
            option: Style options.
            index: Model index.

        Returns:
            The size hint.
        """
        config = index.data(Qt.ItemDataRole.UserRole)
        if not config or not isinstance(config, dict):
            return super().sizeHint(option, index)

        # Calculate height based on content
        name_font = QFont(option.font)
        name_font.setBold(True)
        name_font.setPointSize(name_font.pointSize() + 1)
        name_metrics = QFontMetrics(name_font)

        detail_font = QFont(option.font)
        detail_metrics = QFontMetrics(detail_font)

        # Count detail lines
        c_string = config.get("c_string", "")
        parsed_url = urlparse(c_string)
        host = parsed_url.hostname or config.get("host", "")
        port = parsed_url.port or config.get("port", "")
        database = (
            parsed_url.path[1:]
            if parsed_url.path
            else config.get("database", "")
        )
        username = parsed_url.username or config.get("username", "")
        schema = config.get("schema", "")

        detail_count = 0
        if host or port:
            detail_count += 1
        if database or username:
            detail_count += 1
        if schema:
            detail_count += 1

        # Calculate total height
        icon_size = 32
        padding = 8
        name_height = name_metrics.height()
        detail_height = detail_metrics.height() * detail_count
        spacing = 4 * (detail_count + 1)  # Spacing between lines

        total_height = max(icon_size, name_height + detail_height + spacing) + (
            padding * 2
        )

        base_size = super().sizeHint(option, index)
        return QSize(base_size.width(), max(base_size.height(), total_height))

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        """Paint the item with custom formatting.

        Args:
            painter: The painter to use.
            option: Style options.
            index: Model index.
        """
        config = index.data(Qt.ItemDataRole.UserRole)
        if not config or not isinstance(config, dict):
            super().paint(painter, option, index)
            return

        # Draw selection background
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(option.rect, option.palette.midlight())

        # Parse connection string
        c_string = config.get("c_string", "")
        parsed_url = urlparse(c_string)
        con_type = config.get("type", "")

        # Get icon
        icon = self.get_icon(
            "globe_africa"
            if con_type == CON_TYPE_REMOTE
            else (
                "document_empty"
                if con_type == CON_TYPE_LOCAL
                else "edit_button"
            )
        )
        icon_size = 32
        icon_rect = QRect(
            option.rect.left() + 8,
            option.rect.top() + (option.rect.height() - icon_size) // 2,
            icon_size,
            icon_size,
        )
        icon.paint(painter, icon_rect, Qt.AlignmentFlag.AlignCenter)

        # Text area
        text_left = icon_rect.right() + 12
        text_width = option.rect.width() - text_left - 8
        text_rect = QRect(
            text_left,
            option.rect.top() + 4,
            text_width,
            option.rect.height() - 8,
        )

        # Prepare text content
        name = config.get("name", "")
        db_type = config.get("type", "Unknown")
        display_name = f"{name} ({db_type})"

        host = parsed_url.hostname or config.get("host", "")
        port = parsed_url.port or config.get("port", "")
        database = (
            parsed_url.path[1:]
            if parsed_url.path
            else config.get("database", "")
        )
        username = parsed_url.username or config.get("username", "")
        schema = config.get("schema", "")

        # Build detail lines
        detail_lines = []
        if host or port:
            host_port_parts = []
            if host:
                t_host = self.t("db.config.host", "Host:")
                host_port_parts.append(f"{t_host} {host}")
            if port:
                t_port = self.t("db.config.port", "Port:")
                host_port_parts.append(f"{t_port} {port}")
            if host_port_parts:
                detail_lines.append(" • ".join(host_port_parts))

        if database or username:
            db_user_parts = []
            if database:
                t_database = self.t("db.config.database", "Database:")
                db_user_parts.append(f"{t_database} {database}")
            if username:
                t_username = self.t("db.config.username", "User:")
                db_user_parts.append(f"{t_username} {username}")
            if db_user_parts:
                detail_lines.append(" • ".join(db_user_parts))

        if schema:
            t_schema = self.t("db.config.schema", "Schema:")
            detail_lines.append(f"{t_schema} {schema}")

        # Draw text
        painter.save()
        text_color = (
            option.palette.highlightedText().color()
            if option.state & QStyle.StateFlag.State_Selected
            else option.palette.text().color()
        )
        painter.setPen(text_color)

        # Draw name (bold, larger)
        name_font = QFont(option.font)
        name_font.setBold(True)
        name_font.setPointSize(name_font.pointSize() + 1)
        painter.setFont(name_font)
        name_metrics = QFontMetrics(name_font)
        name_height = name_metrics.height()

        name_rect = QRect(
            text_rect.left(),
            text_rect.top(),
            text_rect.width(),
            name_height,
        )
        painter.drawText(
            name_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            display_name,
        )

        # Draw details (normal font)
        detail_font = QFont(option.font)
        painter.setFont(detail_font)
        detail_metrics = QFontMetrics(detail_font)
        detail_height = detail_metrics.height()
        line_spacing = 4

        detail_y = name_rect.bottom() + line_spacing
        for line in detail_lines:
            detail_rect = QRect(
                text_rect.left(),
                detail_y,
                text_rect.width(),
                detail_height,
            )
            painter.drawText(
                detail_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                line,
            )
            detail_y += detail_height + line_spacing

        painter.restore()
