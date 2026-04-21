"""Tests for cross-process safe settings merge and persistence."""

import os
import threading
from unittest.mock import patch

import yaml
from pyrsistent import freeze

from exdrf_qt.local_settings import (
    LocalSettings,
    merge_c_strings_lists,
    merge_disk_with_memory,
)


class TestMergeCStringsLists:
    """Tests for ``merge_c_strings_lists``."""

    def test_memory_wins_same_id(self) -> None:
        disk = freeze([{"id": "a", "name": "old"}])
        mem = freeze([{"id": "a", "name": "new"}])
        out = merge_c_strings_lists(disk, mem)
        assert list(out) == [{"id": "a", "name": "new"}]

    def test_disk_only_row_kept(self) -> None:
        disk = freeze([{"id": "a", "name": "A"}, {"id": "b", "name": "B"}])
        mem = freeze([{"id": "b", "name": "B2"}])
        out = merge_c_strings_lists(disk, mem)
        rows = list(out)
        by_id = {r["id"]: r["name"] for r in rows}
        assert by_id == {"a": "A", "b": "B2"}

    def test_appends_new_id_from_memory(self) -> None:
        disk = freeze([{"id": "a", "name": "A"}])
        mem = freeze([{"id": "b", "name": "B"}])
        out = merge_c_strings_lists(disk, mem)
        assert [r["id"] for r in list(out)] == ["a", "b"]


class TestMergeDiskWithMemory:
    """Tests for ``merge_disk_with_memory``."""

    def test_preserves_disk_only_top_level_key(self) -> None:
        disk = freeze({"only_disk": 1, "both": 0})
        mem = freeze({"both": 2})
        m = merge_disk_with_memory(disk, mem)
        assert m["only_disk"] == 1
        assert m["both"] == 2

    def test_nested_overlay(self) -> None:
        disk = freeze({"exdrf": freeze({"db": freeze({"x": 1})})})
        mem = freeze({"exdrf": freeze({"db": freeze({"y": 2})})})
        m = merge_disk_with_memory(disk, mem)
        assert m["exdrf"]["db"]["x"] == 1
        assert m["exdrf"]["db"]["y"] == 2

    def test_c_strings_merge_by_id(self) -> None:
        disk = freeze(
            {
                "exdrf": freeze(
                    {
                        "db": freeze(
                            {
                                "c_strings": freeze(
                                    [
                                        {"id": "a", "name": "A"},
                                        {"id": "b", "name": "B_disk"},
                                    ]
                                )
                            }
                        )
                    }
                )
            }
        )
        mem = freeze(
            {
                "exdrf": freeze(
                    {
                        "db": freeze(
                            {
                                "c_strings": freeze(
                                    [
                                        {"id": "b", "name": "B_mem"},
                                        {"id": "c", "name": "C"},
                                    ]
                                )
                            }
                        )
                    }
                )
            }
        )
        out = merge_disk_with_memory(disk, mem)
        rows = list(out["exdrf"]["db"]["c_strings"])
        by_id = {r["id"]: r["name"] for r in rows}
        assert by_id == {"a": "A", "b": "B_mem", "c": "C"}
        assert [r["id"] for r in rows] == ["a", "b", "c"]


class TestLocalSettingsPersistence:
    """Integration tests for locked save and merge."""

    @patch("exdrf_qt.local_settings.user_config_dir")
    def test_concurrent_save_merges_distinct_keys(
        self, mock_ud: object, tmp_path: object
    ) -> None:
        mock_ud.return_value = str(tmp_path)

        def work(name: str) -> None:
            ls = LocalSettings()
            ls.set_setting(f"race.{name}", name)
            ls._do_save_settings()

        t1 = threading.Thread(target=work, args=("one",))
        t2 = threading.Thread(target=work, args=("two",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        path = os.path.join(str(tmp_path), "settings.yaml")
        with open(path, "r", encoding="utf8") as f:
            data = yaml.safe_load(f)
        assert data["race"]["one"] == "one"
        assert data["race"]["two"] == "two"

    @patch("exdrf_qt.local_settings.user_config_dir")
    def test_save_uses_unique_temp_and_atomic_replace(
        self, mock_ud: object, tmp_path: object
    ) -> None:
        mock_ud.return_value = str(tmp_path)
        ls = LocalSettings()
        ls.set_setting("k", 1)
        ls._do_save_settings()
        names = os.listdir(str(tmp_path))
        assert "settings.yaml" in names
        assert not any(n.endswith(".yaml.tmp") for n in names)
