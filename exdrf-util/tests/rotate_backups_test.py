"""Tests for :func:`~exdrf_util.rotate_backups.rotate_backups`."""

from __future__ import annotations

from pathlib import Path

from exdrf_util.rotate_backups import rotate_backups


class TestRotateBackups:
    """Backup rotation for a single file."""

    def test_creates_and_shifts_backups(self, tmp_path: Path) -> None:
        """Each rotation copies the current file and shifts older backups."""

        settings = tmp_path / "settings.json"
        settings.write_text("v1", encoding="utf-8")

        assert rotate_backups(str(settings), max_backups=2) is True
        backup1 = tmp_path / "settings.backup-1.json"
        backup2 = tmp_path / "settings.backup-2.json"
        assert backup1.read_text(encoding="utf-8") == "v1"
        assert not backup2.exists()

        settings.write_text("v2", encoding="utf-8")
        assert rotate_backups(str(settings), max_backups=2) is True
        assert backup1.read_text(encoding="utf-8") == "v2"
        assert backup2.read_text(encoding="utf-8") == "v1"

    def test_missing_file_returns_false(self, tmp_path: Path) -> None:
        """Rotation is a no-op when the source file does not exist."""

        missing = tmp_path / "missing.json"
        assert rotate_backups(str(missing)) is False
