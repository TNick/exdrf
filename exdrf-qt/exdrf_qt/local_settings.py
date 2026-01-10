import logging
import os
import threading
from typing import Any, Dict, List, Optional
from uuid import uuid4

import yaml
from appdirs import user_config_dir
from attrs import define, field
from exdrf_util.rotate_backups import rotate_backups
from pyrsistent import freeze, pmap, thaw
from pyrsistent.typing import PMap

DEBOUNCE_TIME = 5
logger = logging.getLogger(__name__)


@define
class LocalSettings:
    """Local settings for the application."""

    settings: PMap[str, Any] = field(default=pmap())
    _save_timer: Optional[threading.Timer] = field(default=None, init=False)
    _save_lock: threading.Lock = field(factory=threading.Lock, init=False)

    def __attrs_post_init__(self):
        self.load_settings()

    def __getitem__(self, key: str) -> Any:
        return self.get_setting(key)

    def __setitem__(self, key: str, value: Any):
        self.set_setting(key, value)

    def set_read_only(self, read_only: bool):
        """Set the read-only flag for the settings."""
        if read_only:
            self._save_lock = None  # type: ignore
        elif self._save_lock is None:
            self._save_lock = threading.Lock()

    def _debounced_save(self):
        """Internal method to handle debounced saving of settings."""
        if self._save_lock is None:
            return
        try:
            with self._save_lock:
                self._save_timer = None
                self._do_save_settings()
        except Exception as e:
            logger.error(f"Error saving settings: {e}")

    def _do_save_settings(self):
        """Internal method to perform the actual save operation."""
        settings_file = self.settings_file()
        tmp_settings = f"{settings_file}.tmp"
        with open(tmp_settings, "w") as f:
            yaml.dump(thaw(self.settings), f)
        if os.path.exists(settings_file):
            os.remove(settings_file)
        os.rename(tmp_settings, settings_file)

    def save_settings(self):
        """Save the settings to the user's configuration directory with
        debouncing.
        """
        if self._save_lock is None:
            return
        with self._save_lock:
            if self._save_timer is not None:
                self._save_timer.cancel()
            self._save_timer = threading.Timer(
                DEBOUNCE_TIME, self._debounced_save
            )
            self._save_timer.start()

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a local read-write setting.

        Args:
            key: The key of the setting to get as a dot-separated path.
        """
        parts = key.split(".")
        current: Any = self.settings
        for part in parts[:-1]:
            if not hasattr(current, "get"):
                return default
            current = current.get(part)
            if current is None:
                return default
        if not hasattr(current, "get"):
            return default
        return current.get(parts[-1], default)

    def set_setting(self, key: str, value: Any):
        """Set a local read-write setting.

        Args:
            key: The key of the setting to set as a dot-separated path.
            value: The value to set the setting to.
        """
        # logger.debug(f"attempting to change setting '{key}' to {value}")
        parts = key.split(".")

        parents = []
        current = self.settings
        for part in parts[:-1]:
            parents.append((part, current))
            current = current.get(part, freeze({}))

        # If the value is the same as the old value, do nothing.
        old_value = current.get(parts[-1], None)
        if old_value == value:
            # logger.debug(f"setting '{key}' unchanged")
            return

        # Update the value in the target container.
        new_current = current.set(parts[-1], value)

        # Walk back up the path, updating parents.
        for part, parent in reversed(parents):
            new_current = parent.set(part, new_current)

        self.settings = new_current

        # logger.debug(f"setting '{key}' changed to {value} (old: {old_value})")

        # Schedule a save.
        self.save_settings()

    def load_settings(self):
        """Load the settings from the user's configuration directory."""
        settings_file = self.settings_file()
        if os.path.exists(settings_file):
            rotate_backups(settings_file, max_backups=5)
            with open(settings_file, "r") as f:
                tmp = freeze(yaml.safe_load(f))
                if tmp is not None:
                    self.settings = tmp
                else:
                    logger.warning(f"settings file {settings_file} is empty")
            logger.debug(f"settings loaded from {settings_file}")
        else:
            logger.warning(f"settings file {settings_file} does not exist")

    def settings_file(self) -> str:
        """Get the path to the settings file."""
        config_dir = user_config_dir("exdrf")
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        return os.path.join(config_dir, "settings.yaml")

    def remove_db_config(self, id: str):
        """Remove a database configuration from the settings."""
        stg_list = thaw(self["exdrf.db.c_strings"]) or []
        stg_list = [c for c in stg_list if c["id"] != id]
        self["exdrf.db.c_strings"] = freeze(stg_list)

    def add_db_config(
        self,
        id: str,
        name: str,
        kind: str,
        c_string: str,
        schema: str,
        created_at: Optional[str] = None,
    ):
        """Add a database configuration to the settings.

        Args:
            id: The unique identifier for the configuration.
            name: The name of the configuration.
            kind: The type/kind of the configuration.
            c_string: The connection string.
            schema: The schema name.
            created_at: Optional ISO format datetime string for when the
                configuration was created.
        """
        setting = {
            "id": id,
            "name": name,
            "type": kind,
            "c_string": c_string,
            "schema": schema,
        }
        if created_at is not None:
            setting["created_at"] = created_at
        stg_list = thaw(self["exdrf.db.c_strings"]) or []
        stg_list.append(setting)
        self["exdrf.db.c_strings"] = freeze(stg_list)

    def update_db_config(
        self,
        id: str,
        name: str,
        kind: str,
        c_string: str,
        schema: str,
        created_at: Optional[str] = None,
    ):
        """Update a database configuration in the settings.

        If the configuration is not found, a new configuration is created.

        Args:
            id: The ID of the database configuration to update.
            name: The name of the database configuration.
            kind: The kind of the database configuration. This is a translated
                string that can indicate either a local or remote database.
                Not used by the logic; is simply shows in the UI.
            c_string: The connection string of the database configuration.
            schema: The schema of the database configuration.
            created_at: Optional ISO format datetime string for when the
                configuration was created. If None, preserves existing value.
        """
        stg_list: List[Dict[str, Any]] = thaw(self["exdrf.db.c_strings"]) or []
        new_list = []
        for stg in stg_list:
            if stg["id"] == id:
                new_stg = {
                    "id": id,
                    "name": name,
                    "type": kind,
                    "c_string": c_string,
                    "schema": schema,
                }
                # Preserve created_at if it exists, or set it if provided
                if "created_at" in stg:
                    new_stg["created_at"] = stg["created_at"]
                elif created_at is not None:
                    new_stg["created_at"] = created_at
                stg = new_stg
            else:
                stg = stg.copy()
            new_list.append(stg)
        self["exdrf.db.c_strings"] = freeze(new_list)

    def get_db_configs(self) -> List[Dict[str, Any]]:
        """Get all database configurations from the settings."""
        return thaw(self["exdrf.db.c_strings"]) or []

    def locate_db_config(
        self,
        c_string: str,
        schema: str,
        name: Optional[str] = None,
        create: bool = False,
    ) -> Optional[str]:
        """Locate a database configuration in the settings.

        If the configuration is not found and `create` is True, a new
        configuration is created and its ID is returned.

        Args:
            name: The name of the database configuration.
            c_string: The connection string of the database configuration.
            schema: The schema of the database configuration.
        """
        stg_list: List[Dict[str, Any]] = self["exdrf.db.c_strings"] or []
        for stg in stg_list:
            if (
                (name is None or stg["name"] == name)
                and stg["c_string"] == c_string
                and stg["schema"] == schema
            ):
                return stg["id"]

        if create:
            new_id = str(uuid4())
            self.add_db_config(
                id=new_id,
                name=name or "",
                kind="",
                c_string=c_string,
                schema=schema,
            )
            return new_id

        logger.debug(
            "No database configuration found for %s %s %s",
            name,
            c_string,
            schema,
        )
        return None
