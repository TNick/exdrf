import logging
from typing import List

from PyQt5.QtCore import QThread, pyqtSignal

from exdrf_qt.controls.seldb.manage_model import DatabaseConfig, DbVersionInfo

logger = logging.getLogger(__name__)


class DbVersionCheckerWorker(QThread):
    """Worker thread that checks database versions for all configurations.

    This worker goes through each database configuration, attempts to connect,
    and determines the Alembic version status.

    Signals:
        version_checked: Emitted when a version check is complete for a
            configuration. Parameters: config_id, version_info dict.
    """

    version_checked = pyqtSignal(str, dict)  # config_id, version_info

    def __init__(
        self,
        configs: List["DatabaseConfig"],
        migrations_dir: str,
        parent=None,
    ):
        """Initialize the worker.

        Args:
            configs: List of configuration dictionaries to check.
            migrations_dir: Directory containing Alembic migrations.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self._configs = configs
        self._migrations_dir = migrations_dir

    def run(self):
        """Run the version checks for all configurations."""
        from exdrf_al.connection import DbConn

        for config in self._configs:
            config_id = config.get("id", "")
            c_string = config.get("c_string", "")
            schema = config.get("schema", "public")

            if not c_string:
                version_info: "DbVersionInfo" = {
                    "status": "failed",
                    "version": "",
                    "color_status": None,
                    "tooltip": "No connection string provided",
                }
                self.version_checked.emit(config_id, version_info)
                continue

            try:
                # Create a connection
                db_conn = DbConn(c_string=c_string, schema=schema)
                db_conn.connect()

                # Get migration handler
                mgh = db_conn.get_migration_handler(
                    mig_loc=self._migrations_dir
                )

                # Get current version
                current_version = mgh.get_current_version()

                if current_version is None:
                    # Table doesn't exist or is empty
                    version_info = {
                        "status": "no_table",
                        "version": "",
                        "color_status": None,
                        "tooltip": "Alembic version table does not exist",
                    }
                else:
                    # Get history to determine version status
                    history = mgh.get_history()
                    if not history:
                        version_info = {
                            "status": "ok",
                            "version": current_version,
                            "color_status": "red",
                            "tooltip": (
                                f"Version: {current_version}\n"
                                "Status: Outside version chain "
                                "(no migrations found)"
                            ),
                        }
                    else:
                        # Get latest version using the migration handler
                        latest_version = mgh.get_latest_version()

                        # Check if current version is in history
                        version_revisions = {rev[0] for rev in history}
                        if current_version not in version_revisions:
                            # Version is not in the chain
                            version_info = {
                                "status": "ok",
                                "version": current_version,
                                "color_status": "red",
                                "tooltip": (
                                    f"Version: {current_version}\n"
                                    "Status: Outside version chain "
                                    "(no upgrade path)"
                                ),
                            }
                        elif current_version == latest_version:
                            # Current version matches latest
                            version_info = {
                                "status": "ok",
                                "version": current_version,
                                "color_status": "green",
                                "tooltip": (
                                    f"Version: {current_version}\n"
                                    "Status: Current version "
                                    "(matches latest)"
                                ),
                            }
                        else:
                            # Behind current version
                            version_info = {
                                "status": "ok",
                                "version": current_version,
                                "color_status": "yellow",
                                "tooltip": (
                                    f"Version: {current_version}\n"
                                    f"Latest: {latest_version}\n"
                                    "Status: Behind current version "
                                    "(can upgrade)"
                                ),
                            }

                # Close the connection
                db_conn.close()

            except Exception as e:
                # Check for specific errors
                error_str = str(e)
                if (
                    "UndefinedTable" in error_str
                    or "no such table" in error_str.lower()
                ):
                    version_info = {
                        "status": "no_table",
                        "version": "",
                        "color_status": None,
                        "tooltip": "Alembic version table does not exist",
                    }
                elif (
                    "malformed" in error_str.lower()
                    or "column" in error_str.lower()
                ):
                    version_info = {
                        "status": "malformed",
                        "version": "",
                        "color_status": None,
                        "tooltip": (
                            "Alembic version table is malformed: "
                            f"{error_str}"
                        ),
                    }
                else:
                    # Connection failed or other error
                    version_info = {
                        "status": "failed",
                        "version": "",
                        "color_status": None,
                        "tooltip": f"Failed to connect: {error_str}",
                    }
                logger.error(
                    "Error checking database version for %s: %s",
                    config_id,
                    error_str,
                    exc_info=True,
                )

            # Emit the result
            self.version_checked.emit(config_id, version_info)
