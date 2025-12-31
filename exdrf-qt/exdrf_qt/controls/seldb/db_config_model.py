from typing import TYPE_CHECKING, Any, Dict, Optional
from urllib.parse import urlparse

from PyQt5.QtCore import QModelIndex, Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel

from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.seldb.utils import (
    CON_TYPE_CURRENT,
    CON_TYPE_LOCAL,
    CON_TYPE_REMOTE,
)

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401


class DbConfigModel(QStandardItemModel, QtUseContext):
    """A model for displaying database connection configurations.

    Each row represents a database configuration with rich display data.
    The model stores the config dict as item data.

    Attributes:
        ctx: The Qt context.
    """

    ctx: "QtContext"

    def __init__(self, ctx: "QtContext", parent=None):
        """Initialize the model.

        Args:
            ctx: The Qt context.
            parent: Optional parent object.
        """
        super().__init__(parent)
        self.ctx = ctx

    def _build_tooltip(self, config: Dict[str, Any]) -> str:
        """Build tooltip text from configuration.

        Args:
            config: The database configuration dictionary.

        Returns:
            Tooltip text with all fields in "Label: Value" format.
        """
        c_string = config.get("c_string", "")
        parsed_url = urlparse(c_string)

        # Extract values, preferring parsed URL over config dict
        name = config.get("name", "")
        con_type = config.get("type", "")
        schema = config.get("schema", "")
        host = parsed_url.hostname or config.get("host", "")
        port = (
            str(parsed_url.port) if parsed_url.port else config.get("port", "")
        )
        database = (
            parsed_url.path[1:]
            if parsed_url.path
            else config.get("database", "")
        )
        username = parsed_url.username or config.get("username", "")
        scheme = parsed_url.scheme or ""

        # Build tooltip lines
        lines = []
        t_name = self.t("db.config.tooltip.name", "Name:")
        lines.append(f"{t_name} {name}")

        t_type = self.t("db.config.tooltip.type", "Type:")
        lines.append(f"{t_type} {con_type}")

        t_scheme = self.t("db.config.tooltip.scheme", "Protocol:")
        lines.append(f"{t_scheme} {scheme}")

        t_host = self.t("db.config.tooltip.host", "Host:")
        lines.append(f"{t_host} {host}")

        t_port = self.t("db.config.tooltip.port", "Port:")
        lines.append(f"{t_port} {port}")

        t_database = self.t("db.config.tooltip.database", "Database:")
        lines.append(f"{t_database} {database}")

        t_username = self.t("db.config.tooltip.username", "Username:")
        lines.append(f"{t_username} {username}")

        t_schema = self.t("db.config.tooltip.schema", "Schema:")
        lines.append(f"{t_schema} {schema}")

        return "\n".join(lines)

    def add_config(self, config: Dict[str, Any]) -> QStandardItem:
        """Add a database configuration to the model.

        Args:
            config: The database configuration dictionary.

        Returns:
            The created QStandardItem.
        """
        item = QStandardItem()

        # Set display text
        name = config.get("name", "")
        db_type = config.get("type", "Unknown")
        display_name = f"{name} ({db_type})"
        item.setData(display_name, Qt.ItemDataRole.DisplayRole)

        # Set icon
        con_type = config.get("type", "")
        icon_name = (
            "globe_africa"
            if con_type == CON_TYPE_REMOTE
            else (
                "document_empty"
                if con_type == CON_TYPE_LOCAL
                else "edit_button"
            )
        )
        icon = self.get_icon(icon_name)
        item.setData(icon, Qt.ItemDataRole.DecorationRole)

        # Set tooltip
        tooltip = self._build_tooltip(config)
        item.setData(tooltip, Qt.ItemDataRole.ToolTipRole)

        # Set config data
        item.setData(config, Qt.ItemDataRole.UserRole)
        self.appendRow(item)
        return item

    def get_config(self, index: QModelIndex) -> Optional[Dict[str, Any]]:
        """Get the configuration dictionary for the given index.

        Args:
            index: The model index.

        Returns:
            The configuration dictionary or None if invalid.
        """
        if not index.isValid():
            return None
        item = self.itemFromIndex(index)
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def find_config_index(self, config_id: str) -> Optional[QModelIndex]:
        """Find the index of a configuration by its ID.

        Args:
            config_id: The configuration ID to find.

        Returns:
            The model index or None if not found.
        """
        for row in range(self.rowCount()):
            index = self.index(row, 0)
            config = self.get_config(index)
            if config and config.get("id") == config_id:
                return index
        return None

    def populate_db_connections(self):
        """Populate the combobox with database connections."""
        from exdrf_qt.controls.seldb.utils import parse_sqlalchemy_conn_str

        self.clear()
        configs = self.ctx.stg.get_db_configs()

        for config in configs:
            self.add_config(config)

        # Add current connection if not in list
        if self.ctx.c_string:
            found = self.ctx.stg.locate_db_config(
                self.ctx.c_string, self.ctx.schema
            )
            if not found:

                current_config = {
                    **parse_sqlalchemy_conn_str(self.ctx.c_string),
                    "id": "current",
                    "name": self.ctx.t(
                        "excel.dialog.current_connection", "Current"
                    ),
                    "type": CON_TYPE_CURRENT,
                    "c_string": self.ctx.c_string,
                    "schema": self.ctx.schema or "",
                }
                if "password" in current_config:
                    del current_config["password"]
                # Insert at the beginning
                item = QStandardItem()

                # Set display text
                display_name = (
                    f"{current_config['name']} ({current_config['type']})"
                )
                item.setData(display_name, Qt.ItemDataRole.DisplayRole)

                # Set icon
                icon = self.get_icon("edit_button")
                item.setData(icon, Qt.ItemDataRole.DecorationRole)

                # Set tooltip
                tooltip = self._build_tooltip(current_config)
                item.setData(tooltip, Qt.ItemDataRole.ToolTipRole)

                # Set config data
                item.setData(current_config, Qt.ItemDataRole.UserRole)
                self.insertRow(0, item)
