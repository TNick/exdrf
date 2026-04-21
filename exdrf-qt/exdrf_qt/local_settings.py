import logging
import os
import threading
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import yaml
from appdirs import user_config_dir
from attrs import define, field
from exdrf_util.rotate_backups import rotate_backups
from filelock import FileLock, Timeout
from pyrsistent import PMap, freeze, pmap, thaw

DEBOUNCE_TIME = 5
MAX_BACKUPS = 5
LOCK_TIMEOUT = 30
# Path tuple for list merge-by-id (``exdrf.db.c_strings``).
C_STRINGS_PATH: Tuple[str, ...] = ("exdrf", "db", "c_strings")
logger = logging.getLogger(__name__)


def merge_c_strings_lists(disk_val: Any, mem_val: Any) -> Any:
    """Merge two ``c_strings`` list values by ``id``; memory wins on conflicts.

    Disk row order is preserved; rows only in memory are appended.

    Args:
        disk_val: Previous list from disk (may be None).
        mem_val: List from the current process (may be None).

    Returns:
        Frozen merged list.
    """
    d_rows: List[Any] = (
        list(thaw(disk_val) or []) if disk_val is not None else []
    )
    m_rows: List[Any] = list(thaw(mem_val) or []) if mem_val is not None else []
    mem_by_id: Dict[str, Dict[str, Any]] = {}
    for row in m_rows:
        r = dict(thaw(row)) if not isinstance(row, dict) else dict(row)
        rid = r.get("id")
        if rid is not None:
            mem_by_id[str(rid)] = r
    merged: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for row in d_rows:
        r = dict(thaw(row)) if not isinstance(row, dict) else dict(row)
        rid = r.get("id")
        if rid is not None and str(rid) in mem_by_id:
            merged.append(mem_by_id[str(rid)])
            seen.add(str(rid))
        else:
            merged.append(r)
    for row in m_rows:
        r = dict(thaw(row)) if not isinstance(row, dict) else dict(row)
        rid = r.get("id")
        if rid is not None and str(rid) not in seen:
            merged.append(r)
            seen.add(str(rid))
    return freeze(merged)


def _overlay_merge(
    disk: Any,
    memory: Any,
    path: Tuple[str, ...],
) -> Any:
    """Overlay ``memory`` onto ``disk`` for nested maps."""
    if not isinstance(memory, PMap):
        return memory
    if not isinstance(disk, PMap):
        disk = pmap()
    result = disk
    for k, v_mem in memory.items():
        v_disk = disk.get(k)
        new_path = path + (k,)
        if new_path == C_STRINGS_PATH:
            merged_val = merge_c_strings_lists(v_disk, v_mem)
            result = result.set(k, merged_val)
        elif isinstance(v_mem, PMap):
            if isinstance(v_disk, PMap):
                merged_val = _overlay_merge(v_disk, v_mem, new_path)
            else:
                merged_val = _overlay_merge(pmap(), v_mem, new_path)
            result = result.set(k, merged_val)
        else:
            result = result.set(k, v_mem)
    return result


def merge_disk_with_memory(disk: Any, memory: Any) -> PMap[str, Any]:
    """Combine on-disk settings with in-memory settings for saving.

    Keys present only on disk are kept. Nested maps are merged recursively.
    For ``exdrf.db.c_strings``, list entries are merged by ``id``.

    Args:
        disk: Frozen mapping loaded from YAML (typically a ``PMap``).
        memory: Current in-memory ``self.settings``.

    Returns:
        Frozen mapping to persist.
    """
    if not isinstance(memory, PMap):
        return freeze(memory) if memory is not None else pmap()
    if not isinstance(disk, PMap):
        disk = pmap()
    return _overlay_merge(disk, memory, ())


@define
class LocalSettings:
    """Local settings for the application.

    Saves merge in-memory state with the current on-disk file under a
    cross-process file lock so concurrent instances do not overwrite each
    other's keys. ``exdrf.db.c_strings`` entries are merged by ``id``;
    other list values follow overlay semantics (concurrent edits to the same
    list may still race).

    Attributes:
        settings: Immutable mapping of stored settings.
        read_only: Flag indicating whether persistence is disabled.
        _save_timer: Debounce timer for saves (None when inactive).
        _save_lock: Lock guarding saves; None when read_only is True.
    """

    settings: PMap[str, Any] = field(default=pmap())
    read_only: bool = field(default=False)
    _save_timer: Optional[threading.Timer] = field(default=None, init=False)
    _save_lock: Optional[threading.Lock] = field(
        factory=threading.Lock, init=False
    )

    def __attrs_post_init__(self):
        self.set_read_only(self.read_only)
        self.load_settings()

    def __getitem__(self, key: str) -> Any:
        return self.get_setting(key)

    def __setitem__(self, key: str, value: Any):
        self.set_setting(key, value)

    def set_read_only(self, read_only: bool):
        """Set the read-only flag for the settings."""
        self.read_only = read_only
        if read_only:
            self._save_lock = None
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
            logger.error("Error saving settings: %s", e, exc_info=True)

    def _do_save_settings(self):
        """Internal method to perform the actual save operation."""
        if self.read_only:
            return
        settings_file = self.settings_file()
        lock_path = f"{settings_file}.lock"
        try:
            with FileLock(lock_path, timeout=LOCK_TIMEOUT):
                disk_pm: PMap[str, Any] = pmap()
                if os.path.exists(settings_file):
                    with open(settings_file, "r") as f:
                        loaded = yaml.safe_load(f)
                        if loaded is not None:
                            disk_pm = freeze(loaded)
                to_save = merge_disk_with_memory(disk_pm, self.settings)
                config_dir = os.path.dirname(settings_file)
                tmp_settings = os.path.join(
                    config_dir,
                    f"settings.{uuid4()}.yaml.tmp",
                )
                try:
                    with open(tmp_settings, "w") as f:
                        yaml.dump(thaw(to_save), f)
                    os.replace(tmp_settings, settings_file)
                except Exception:
                    if os.path.exists(tmp_settings):
                        try:
                            os.remove(tmp_settings)
                        except OSError as rm_err:
                            logger.log(
                                1,
                                "Could not remove temp settings file %s: %s",
                                tmp_settings,
                                rm_err,
                            )
                    raise
        except Timeout:
            logger.error(
                "Timed out acquiring settings lock for save (timeout=%ss)",
                LOCK_TIMEOUT,
                exc_info=True,
            )

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
        if not os.path.exists(settings_file):
            logger.warning("settings file %s does not exist", settings_file)
            return

        lock_path = f"{settings_file}.lock"

        def _load_rotating() -> None:
            if not self.read_only:
                rotate_backups(settings_file, max_backups=MAX_BACKUPS)
            with open(settings_file, "r") as f:
                raw = yaml.safe_load(f)
                tmp = freeze(raw)
                if tmp is not None:
                    self.settings = tmp
                else:
                    logger.warning("settings file %s is empty", settings_file)

        def _load_plain() -> None:
            with open(settings_file, "r") as f:
                raw = yaml.safe_load(f)
                tmp = freeze(raw)
                if tmp is not None:
                    self.settings = tmp
                else:
                    logger.warning("settings file %s is empty", settings_file)

        try:
            with FileLock(lock_path, timeout=LOCK_TIMEOUT):
                _load_rotating()
        except Timeout:
            logger.error(
                "Timed out acquiring settings lock for load (timeout=%ss); "
                "loading without lock",
                LOCK_TIMEOUT,
                exc_info=True,
            )
            _load_plain()
        logger.debug("settings loaded from %s", settings_file)

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
