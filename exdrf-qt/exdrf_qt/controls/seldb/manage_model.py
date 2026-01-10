import logging
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional, TypedDict, cast

import humanize
from PyQt5.QtCore import (
    QAbstractItemModel,
    QModelIndex,
    Qt,
)
from PyQt5.QtGui import QColor

from exdrf_qt.controls.seldb.utils import parse_sqlalchemy_conn_str

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401


class ParsedConnectionString(TypedDict, total=False):
    """TypedDict for parsed connection string components.

    Attributes:
        scheme: The database scheme (e.g., "postgresql", "mysql").
        username: The username for authentication.
        password: The password for authentication.
        host: The host address.
        port: The port number.
        database: The database name.
        params: Additional connection parameters.
    """

    scheme: Optional[str]
    username: Optional[str]
    password: Optional[str]
    host: Optional[str]
    port: Optional[str]
    database: Optional[str]
    params: Optional[str]


class DbVersionInfo(TypedDict, total=False):
    """TypedDict for database version information.

    Attributes:
        status: The status of the version check. One of: "checking",
            "failed", "no_table", "malformed", or "ok".
        version: The version string if available, empty string otherwise.
        color_status: The color status for display. One of: "green",
            "yellow", "red", or None.
        tooltip: Optional custom tooltip text with detailed information.
    """

    status: str
    version: str
    color_status: Optional[str]
    tooltip: Optional[str]


class DatabaseConfig(TypedDict, total=False):
    """TypedDict for database configuration dictionary.

    Attributes:
        id: The unique identifier for the configuration.
        name: The name of the configuration.
        type: The type/kind of the configuration (e.g., "Local", "Remote").
        c_string: The connection string.
        schema: The schema name.
        created_at: Optional ISO format datetime string for when the
            configuration was created.
        _parsed: Internal parsed connection string components.
        _db_version_info: Internal database version information.
    """

    id: str
    name: str
    type: str
    c_string: str
    schema: str
    created_at: Optional[str]
    _parsed: Dict[str, Optional[str]]
    _db_version_info: Dict[str, Any]


logger = logging.getLogger(__name__)


COL_NAME = 0
COL_DB_VERSION = 1
COL_TYPE = 2
COL_SCHEMA = 3
COL_CREATED = 4
COL_SCHEME = 5
COL_USERNAME = 6
COL_PASSWORD = 7
COL_HOST = 8
COL_PORT = 9
COL_DATABASE = 10
COL_PARAMS = 11
COL_C_STRING = 12


def _sort_key_name(config: "DatabaseConfig") -> str:
    """Get the name for sorting.

    Args:
        config: The configuration dictionary.

    Returns:
        The name in lowercase for case-insensitive sorting.
    """
    name = config.get("name", "")
    return name.lower() if name else ""


def _sort_key_type(config: "DatabaseConfig") -> str:
    """Get the type for sorting.

    Args:
        config: The configuration dictionary.

    Returns:
        The type in lowercase for case-insensitive sorting.
    """
    type_val = config.get("type", "")
    return type_val.lower() if type_val else ""


def _sort_key_schema(config: "DatabaseConfig") -> str:
    """Get the schema for sorting.

    Args:
        config: The configuration dictionary.

    Returns:
        The schema in lowercase for case-insensitive sorting.
    """
    schema = config.get("schema", "")
    return schema.lower() if schema else ""


def _sort_key_scheme(config: "DatabaseConfig") -> str:
    """Get the scheme for sorting.

    Args:
        config: The configuration dictionary.

    Returns:
        The scheme in lowercase for case-insensitive sorting.
    """
    parsed = config.get("_parsed", {})
    scheme = parsed.get("scheme") if parsed else None
    return scheme.lower() if scheme else ""


def _sort_key_username(config: "DatabaseConfig") -> str:
    """Get the username for sorting.

    Args:
        config: The configuration dictionary.

    Returns:
        The username in lowercase for case-insensitive sorting.
    """
    parsed = config.get("_parsed", {})
    username = parsed.get("username") if parsed else None
    return username.lower() if username else ""


def _sort_key_password(config: "DatabaseConfig") -> str:
    """Get the password for sorting.

    Args:
        config: The configuration dictionary.

    Returns:
        Empty string (password is masked).
    """
    return ""


def _sort_key_host(config: "DatabaseConfig") -> str:
    """Get the host for sorting.

    Args:
        config: The configuration dictionary.

    Returns:
        The host in lowercase for case-insensitive sorting.
    """
    parsed = config.get("_parsed", {})
    host = parsed.get("host") if parsed else None
    return host.lower() if host else ""


def _sort_key_port(config: "DatabaseConfig") -> str:
    """Get the port for sorting.

    Args:
        config: The configuration dictionary.

    Returns:
        The port as a string for sorting.
    """
    parsed = config.get("_parsed", {})
    port = parsed.get("port") if parsed else None
    return port if port else ""


def _sort_key_database(config: "DatabaseConfig") -> str:
    """Get the database for sorting.

    Args:
        config: The configuration dictionary.

    Returns:
        The database in lowercase for case-insensitive sorting.
    """
    parsed = config.get("_parsed", {})
    database = parsed.get("database") if parsed else None
    return database.lower() if database else ""


def _sort_key_params(config: "DatabaseConfig") -> str:
    """Get the params for sorting.

    Args:
        config: The configuration dictionary.

    Returns:
        The params in lowercase for case-insensitive sorting.
    """
    parsed = config.get("_parsed", {})
    params = parsed.get("params") if parsed else None
    return params.lower() if params else ""


def _sort_key_db_version(config: "DatabaseConfig") -> str:
    """Get the DB version for sorting.

    Args:
        config: The configuration dictionary.

    Returns:
        The DB version string for sorting.
    """
    db_version_info = config.get("_db_version_info", {})
    status = db_version_info.get("status", "checking")
    if status == "checking":
        return "zzz_checking"  # Sort to end
    elif status == "failed":
        return "zzz_failed"
    elif status == "no_table":
        return "zzz_no_table"
    elif status == "malformed":
        return "zzz_malformed"
    else:
        return db_version_info.get("version", "")


def _sort_key_c_string(config: "DatabaseConfig") -> str:
    """Get the connection string for sorting.

    Args:
        config: The configuration dictionary.

    Returns:
        The connection string in lowercase for case-insensitive sorting.
    """
    c_string = config.get("c_string", "")
    return c_string.lower() if c_string else ""


def _reconstruct_connection_string(parsed: "ParsedConnectionString") -> str:
    """Reconstruct a connection string from parsed components.

    Args:
        parsed: Dictionary with connection string components.

    Returns:
        The reconstructed connection string.
    """
    scheme = parsed.get("scheme", "")
    username = parsed.get("username", "")
    password = parsed.get("password", "")
    host = parsed.get("host", "")
    port = parsed.get("port", "")
    database = parsed.get("database", "")
    params = parsed.get("params", "")

    # Handle SQLite specially (sqlite:/// with three slashes)
    if scheme and scheme.lower() == "sqlite":
        if database:
            return f"{scheme}:///{database}"
        else:
            return f"{scheme}:///"

    parts = []
    if scheme:
        parts.append(scheme)
    parts.append("://")

    if username or password:
        if username:
            parts.append(username)
        if password:
            parts.append(":")
            parts.append(password)
        parts.append("@")

    if host:
        parts.append(host)

    if port:
        parts.append(":")
        parts.append(port)

    if database:
        parts.append("/")
        parts.append(database)

    if params:
        parts.append("?")
        parts.append(params)

    return "".join(parts)


def _sort_key_created(config: "DatabaseConfig") -> datetime:
    """Get the creation date for sorting.

    Args:
        config: The configuration dictionary.

    Returns:
        The datetime object for sorting, or datetime.min for None values.
    """
    created_at = config.get("created_at")
    if created_at is None:
        # Put None values at the end
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        if isinstance(created_at, str):
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        else:
            dt = created_at
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError, TypeError):
        return datetime.min.replace(tzinfo=timezone.utc)


class DatabaseConfigModel(QAbstractItemModel):
    """Model for managing database configurations in a tree view.

    This model provides a flat list of database configurations with five
    columns: Name, Type, Schema, Connection String, and Created. Items are
    editable and the model stores the configuration ID in the UserRole data
    for the name column.

    Attributes:
        _configs: List of database configuration dictionaries.
        _ctx: The Qt context for accessing settings and translations.
    """

    _configs: List[Dict[str, Any]]
    _ctx: "QtContext"

    def __init__(self, ctx: "QtContext", parent=None):
        """Initialize the model.

        Args:
            ctx: The Qt context for accessing settings and translations.
            parent: The parent QObject.
        """
        super().__init__(parent)
        self._ctx = ctx
        self._configs = []

        # Load initial configurations from settings and parse connection strings
        for item in self._ctx.stg.get_db_configs():
            config = item.copy()
            # Parse connection string components
            c_string = config.get("c_string", "")
            if c_string:
                parsed = parse_sqlalchemy_conn_str(c_string)
                config["_parsed"] = parsed
            else:
                config["_parsed"] = {}
            # Initialize DB version info with checking status
            config["_db_version_info"] = {
                "status": "checking",
                "version": "",
                "color_status": None,
                "tooltip": None,
            }
            self._configs.append(config)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of rows under the given parent.

        Args:
            parent: The parent index. For a flat list, only the root
                index has children.

        Returns:
            The number of rows.
        """
        if parent.isValid():
            return 0
        return len(self._configs)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of columns.

        Args:
            parent: The parent index (unused for flat models).

        Returns:
            The number of columns (13).
        """
        return 13

    def index(
        self, row: int, column: int, parent: QModelIndex = QModelIndex()
    ) -> QModelIndex:
        """Create an index for the given row and column.

        Args:
            row: The row number.
            column: The column number.
            parent: The parent index. For a flat list, this should be
                invalid.

        Returns:
            A valid index if the row and column are valid, otherwise
            an invalid index.
        """
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if parent.isValid():
            return QModelIndex()

        return self.createIndex(row, column)

    def parent(  # type: ignore[override]
        self, child: QModelIndex
    ) -> QModelIndex:
        """Return the parent of the given index.

        Args:
            child: The child index.

        Returns:
            An invalid index since this is a flat list model.
        """
        return QModelIndex()

    def data(
        self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        """Return the data for the given index and role.

        Args:
            index: The model index.
            role: The data role.

        Returns:
            The data for the given role, or None if not available.
        """
        if not index.isValid():
            return None

        if index.row() >= len(self._configs):
            return None

        config = self._configs[index.row()]
        parsed = config.get("_parsed", {})

        if role == Qt.ItemDataRole.DisplayRole:
            if index.column() == COL_NAME:
                return config.get("name", "")
            elif index.column() == COL_TYPE:
                return config.get("type", "")
            elif index.column() == COL_SCHEMA:
                return config.get("schema", "")
            elif index.column() == COL_CREATED:
                created_at = config.get("created_at")
                if created_at is None:
                    return ""
                try:
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(
                            created_at.replace("Z", "+00:00")
                        )
                    else:
                        dt = created_at
                    if not dt.tzinfo:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return humanize.naturaltime(dt)
                except (ValueError, AttributeError, TypeError):
                    return ""
            elif index.column() == COL_SCHEME:
                return parsed.get("scheme", "") or ""
            elif index.column() == COL_USERNAME:
                return parsed.get("username", "") or ""
            elif index.column() == COL_PASSWORD:
                password = parsed.get("password", "")
                return "****" if password else ""
            elif index.column() == COL_HOST:
                return parsed.get("host", "") or ""
            elif index.column() == COL_PORT:
                return parsed.get("port", "") or ""
            elif index.column() == COL_DATABASE:
                database = parsed.get("database", "") or ""
                # If it looks like a file path, show only the filename
                if database and os.sep in database:
                    return os.path.basename(database)
                return database
            elif index.column() == COL_PARAMS:
                return parsed.get("params", "") or ""
            elif index.column() == COL_DB_VERSION:
                db_version_info = config.get("_db_version_info", {})
                status = db_version_info.get("status", "checking")
                if status == "checking":
                    return "..."
                elif status == "failed":
                    return "failed to connect"
                elif status == "no_table":
                    return "no version"
                elif status == "malformed":
                    return "malformed version table"
                else:
                    return db_version_info.get("version", "")
            elif index.column() == COL_C_STRING:
                return config.get("c_string", "")
        elif role == Qt.ItemDataRole.EditRole:
            if index.column() == COL_NAME:
                return config.get("name", "")
            elif index.column() == COL_TYPE:
                return config.get("type", "")
            elif index.column() == COL_SCHEMA:
                return config.get("schema", "")
            elif index.column() == COL_CREATED:
                return config.get("created_at")
            elif index.column() == COL_SCHEME:
                return parsed.get("scheme", "") or ""
            elif index.column() == COL_USERNAME:
                return parsed.get("username", "") or ""
            elif index.column() == COL_PASSWORD:
                return parsed.get("password", "") or ""
            elif index.column() == COL_HOST:
                return parsed.get("host", "") or ""
            elif index.column() == COL_PORT:
                return parsed.get("port", "") or ""
            elif index.column() == COL_DATABASE:
                return parsed.get("database", "") or ""
            elif index.column() == COL_PARAMS:
                return parsed.get("params", "") or ""
            elif index.column() == COL_DB_VERSION:
                db_version_info = config.get("_db_version_info", {})
                return db_version_info.get("version", "")
            elif index.column() == COL_C_STRING:
                return config.get("c_string", "")
        elif role == Qt.ItemDataRole.BackgroundRole:
            if index.column() == COL_DB_VERSION:
                db_version_info = config.get("_db_version_info", {})
                color_status = db_version_info.get("color_status", None)
                if color_status == "green":
                    return QColor(200, 255, 200)  # Light green
                elif color_status == "yellow":
                    return QColor(255, 255, 200)  # Light yellow
                elif color_status == "red":
                    return QColor(255, 200, 200)  # Light red
                return None
        elif role == Qt.ItemDataRole.DecorationRole:
            if index.column() == COL_DB_VERSION:
                db_version_info = config.get("_db_version_info", {})
                status = db_version_info.get("status", "checking")
                color_status = db_version_info.get("color_status", None)

                # Error states: failed, no_table, malformed
                if status in ("failed", "no_table", "malformed"):
                    return self._ctx.get_icon("exclamation")
                # Outside version chain (red)
                elif color_status == "red":
                    return self._ctx.get_icon("cross")
                # Same as current (green)
                elif color_status == "green":
                    return self._ctx.get_icon("tick")
                # Can be upgraded (yellow)
                elif color_status == "yellow":
                    return self._ctx.get_icon("arrow_refresh")
                # Checking or unknown
                return None
        elif role == Qt.ItemDataRole.ToolTipRole:
            if index.column() == COL_CREATED:
                created_at = config.get("created_at")
                if created_at is None:
                    return ""
                try:
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(
                            created_at.replace("Z", "+00:00")
                        )
                    else:
                        dt = created_at
                    if not dt.tzinfo:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt.strftime("%Y-%m-%d %H:%M:%S %Z")
                except (ValueError, AttributeError, TypeError):
                    return ""
            elif index.column() == COL_DB_VERSION:
                db_version_info = config.get("_db_version_info", {})
                tooltip = db_version_info.get("tooltip", "")
                if tooltip:
                    return tooltip
                status = db_version_info.get("status", "checking")
                if status == "checking":
                    return "Checking database version..."
                elif status == "failed":
                    return "Failed to connect to the database"
                elif status == "no_table":
                    return "Alembic version table does not exist"
                elif status == "malformed":
                    return "Alembic version table is malformed"
                else:
                    version = db_version_info.get("version", "")
                    color_status = db_version_info.get("color_status", "")
                    if color_status == "green":
                        return (
                            f"Version: {version}\n"
                            "Status: Current version (matches latest)"
                        )
                    elif color_status == "yellow":
                        return (
                            f"Version: {version}\n"
                            "Status: Behind current version (can upgrade)"
                        )
                    elif color_status == "red":
                        return (
                            f"Version: {version}\n"
                            "Status: Outside version chain (no upgrade path)"
                        )
                    return f"Version: {version}"
            elif index.column() == COL_DATABASE:
                # For database column, show full path in tooltip if it's a path
                parsed = config.get("_parsed", {})
                database = parsed.get("database", "") or ""
                if database and os.sep in database:
                    return database
                # Fall through to default if not a path
            else:
                # Default: show the display value as tooltip
                display_value = self.data(index, Qt.ItemDataRole.DisplayRole)
                if display_value is not None:
                    return str(display_value)
                return ""
        elif role == Qt.ItemDataRole.UserRole:
            if index.column() == COL_NAME:
                return config.get("id", "")

        return None

    def setData(
        self,
        index: QModelIndex,
        value: Any,
        role: int = Qt.ItemDataRole.EditRole,
    ) -> bool:
        """Set the data for the given index and role.

        Args:
            index: The model index.
            value: The new value.
            role: The data role (should be EditRole).

        Returns:
            True if the data was set successfully, False otherwise.
        """
        if not index.isValid():
            return False

        if role != Qt.ItemDataRole.EditRole:
            return False

        if index.row() >= len(self._configs):
            return False

        config = self._configs[index.row()]
        column = index.column()
        parsed = config.get("_parsed", {})
        needs_reconstruct = False

        # Update the config dictionary
        if column == COL_NAME:
            config["name"] = str(value)
        elif column == COL_TYPE:
            config["type"] = str(value)
        elif column == COL_SCHEMA:
            config["schema"] = str(value)
        elif column == COL_CREATED:
            # Created date is not editable, but handle it for completeness
            return False
        elif column == COL_SCHEME:
            parsed["scheme"] = str(value) if value else None
            needs_reconstruct = True
        elif column == COL_USERNAME:
            parsed["username"] = str(value) if value else None
            needs_reconstruct = True
        elif column == COL_PASSWORD:
            parsed["password"] = str(value) if value else None
            needs_reconstruct = True
        elif column == COL_HOST:
            parsed["host"] = str(value) if value else None
            needs_reconstruct = True
        elif column == COL_PORT:
            parsed["port"] = str(value) if value else None
            needs_reconstruct = True
        elif column == COL_DATABASE:
            parsed["database"] = str(value) if value else None
            needs_reconstruct = True
        elif column == COL_PARAMS:
            parsed["params"] = str(value) if value else None
            needs_reconstruct = True
        elif column == COL_C_STRING:
            config["c_string"] = str(value)
            # Re-parse the connection string
            if value:
                parsed_new = parse_sqlalchemy_conn_str(str(value))
                config["_parsed"] = parsed_new
            else:
                config["_parsed"] = {}
        else:
            return False

        # Reconstruct connection string if components were edited
        if needs_reconstruct:
            config["_parsed"] = parsed
            config["c_string"] = _reconstruct_connection_string(parsed)

        # Update the settings
        created_at = config.get("created_at")
        self._ctx.stg.update_db_config(
            id=config["id"],
            name=config["name"],
            kind=config["type"],
            c_string=config["c_string"],
            schema=config["schema"],
            created_at=created_at,
        )

        # Emit dataChanged signal for all affected columns
        if needs_reconstruct or column == COL_C_STRING:
            # Emit for all columns since connection string affects multiple
            top_left = self.index(index.row(), 0)
            bottom_right = self.index(index.row(), self.columnCount() - 1)
            self.dataChanged.emit(top_left, bottom_right, [role])
        else:
            self.dataChanged.emit(index, index, [role])

        return True

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Return the item flags for the given index.

        Args:
            index: The model index.

        Returns:
            The item flags, including ItemIsEditable.
        """
        if not index.isValid():
            return cast(Qt.ItemFlags, Qt.ItemFlag.NoItemFlags)

        flags = Qt.ItemFlag.ItemIsEnabled
        flags |= Qt.ItemFlag.ItemIsSelectable
        # Created date and DB version columns are not editable
        if index.column() not in (COL_CREATED, COL_DB_VERSION):
            flags |= Qt.ItemFlag.ItemIsEditable
        return cast(Qt.ItemFlags, flags)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Return the header data for the given section.

        Args:
            section: The section (column) number.
            orientation: The orientation (horizontal or vertical).
            role: The data role.

        Returns:
            The header text for DisplayRole, or None otherwise.
        """
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
        ):
            if section == COL_NAME:
                return self._ctx.t("cmn.db.name", "Name")
            elif section == COL_DB_VERSION:
                return self._ctx.t("cmn.db.db_version", "DB Version")
            elif section == COL_TYPE:
                return self._ctx.t("cmn.db.type", "Type")
            elif section == COL_SCHEMA:
                return self._ctx.t("cmn.db.schema", "Schema")
            elif section == COL_CREATED:
                return self._ctx.t("cmn.db.created", "Created")
            elif section == COL_SCHEME:
                return self._ctx.t("cmn.db.scheme", "Scheme")
            elif section == COL_USERNAME:
                return self._ctx.t("cmn.db.username", "Username")
            elif section == COL_PASSWORD:
                return self._ctx.t("cmn.db.password", "Password")
            elif section == COL_HOST:
                return self._ctx.t("cmn.db.host", "Host")
            elif section == COL_PORT:
                return self._ctx.t("cmn.db.port", "Port")
            elif section == COL_DATABASE:
                return self._ctx.t("cmn.db.database", "Database")
            elif section == COL_PARAMS:
                return self._ctx.t("cmn.db.params", "Params")
            elif section == COL_C_STRING:
                return self._ctx.t("cmn.db.c_string", "Connection String")

        return None

    def sort(
        self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder
    ) -> None:
        """Sort the model by the specified column.

        Args:
            column: The column to sort by.
            order: The sort order (AscendingOrder or DescendingOrder).
        """
        if column < 0 or column >= self.columnCount():
            return

        # Determine the key function based on the column
        if column == COL_NAME:
            key_func = _sort_key_name
        elif column == COL_TYPE:
            key_func = _sort_key_type
        elif column == COL_SCHEMA:
            key_func = _sort_key_schema
        elif column == COL_CREATED:
            key_func = _sort_key_created
        elif column == COL_SCHEME:
            key_func = _sort_key_scheme
        elif column == COL_USERNAME:
            key_func = _sort_key_username
        elif column == COL_PASSWORD:
            key_func = _sort_key_password
        elif column == COL_HOST:
            key_func = _sort_key_host
        elif column == COL_PORT:
            key_func = _sort_key_port
        elif column == COL_DATABASE:
            key_func = _sort_key_database
        elif column == COL_PARAMS:
            key_func = _sort_key_params
        elif column == COL_DB_VERSION:
            key_func = _sort_key_db_version
        elif column == COL_C_STRING:
            key_func = _sort_key_c_string
        else:
            return

        # Sort the list
        self.beginResetModel()
        reverse = order == Qt.SortOrder.DescendingOrder
        self._configs.sort(
            key=lambda c: key_func(cast("DatabaseConfig", c)),
            reverse=reverse,
        )
        self.endResetModel()

    def add_config(
        self, config_id: str, name: str, kind: str, c_string: str, schema: str
    ) -> QModelIndex:
        """Add a new configuration to the model.

        Args:
            config_id: The unique identifier for the configuration.
            name: The name of the configuration.
            kind: The type/kind of the configuration (e.g., "Local",
                "Remote").
            c_string: The connection string.
            schema: The schema name.

        Returns:
            The model index of the newly added row.
        """
        row = len(self._configs)
        self.beginInsertRows(QModelIndex(), row, row)

        # Set creation date to current time
        created_at = datetime.now(timezone.utc).isoformat()

        # Parse connection string components
        parsed = {}
        if c_string:
            parsed = parse_sqlalchemy_conn_str(c_string)

        config = {
            "id": config_id,
            "name": name,
            "type": kind,
            "c_string": c_string,
            "schema": schema,
            "created_at": created_at,
            "_parsed": parsed,
            "_db_version_info": {
                "status": "checking",
                "version": "",
                "color_status": None,
                "tooltip": None,
            },
        }
        self._configs.append(config)

        # Add to settings
        self._ctx.stg.add_db_config(
            id=config_id,
            name=name,
            kind=kind,
            c_string=c_string,
            schema=schema,
            created_at=created_at,
        )

        self.endInsertRows()

        return self.index(row, COL_NAME)

    def remove_config(self, index: QModelIndex) -> bool:
        """Remove a configuration from the model.

        Args:
            index: The model index of the configuration to remove.

        Returns:
            True if the configuration was removed successfully, False
            otherwise.
        """
        if not index.isValid():
            return False

        row = index.row()
        if row >= len(self._configs):
            return False

        config = self._configs[row]
        config_id = config.get("id", "")

        self.beginRemoveRows(QModelIndex(), row, row)
        self._configs.pop(row)
        self.endRemoveRows()

        # Remove from settings
        self._ctx.stg.remove_db_config(config_id)

        return True

    def get_config(self, index: QModelIndex) -> Optional[Dict[str, Any]]:
        """Get the configuration dictionary for the given index.

        Args:
            index: The model index.

        Returns:
            The configuration dictionary, or None if the index is invalid.
        """
        if not index.isValid():
            return None

        row = index.row()
        if row >= len(self._configs):
            return None

        return self._configs[row].copy()

    def get_config_by_id(self, config_id: str) -> Optional[Dict[str, Any]]:
        """Get a configuration dictionary by its ID.

        Args:
            config_id: The configuration ID.

        Returns:
            The configuration dictionary, or None if not found.
        """
        for config in self._configs:
            if config.get("id") == config_id:
                return cast(Dict[str, Any], config.copy())
        return None

    def update_db_version_info(
        self, config_id: str, version_info: "DbVersionInfo"
    ) -> None:
        """Update the database version information for a configuration.

        Args:
            config_id: The configuration ID.
            version_info: Dictionary with version information containing:
                - status: "checking", "failed", "no_table", "malformed", or
                  "ok"
                - version: The version string (if available)
                - color_status: "green", "yellow", or "red" (if available)
                - tooltip: Optional custom tooltip text
        """
        for i, config in enumerate(self._configs):
            if config.get("id") == config_id:
                config["_db_version_info"] = version_info
                # Emit dataChanged for the DB version column
                # Include DisplayRole, BackgroundRole, DecorationRole,
                # and ToolTipRole
                index = self.index(i, COL_DB_VERSION)
                self.dataChanged.emit(
                    index,
                    index,
                    [
                        Qt.ItemDataRole.DisplayRole,
                        Qt.ItemDataRole.BackgroundRole,
                        Qt.ItemDataRole.DecorationRole,
                        Qt.ItemDataRole.ToolTipRole,
                    ],
                )
                break
