"""Tests for monorepo release tag parsing and package path resolution."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS = _REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from exdrf_repo_paths import resolve_publish_package_dir  # noqa: E402
from release_tag import (  # noqa: E402
    assert_release_version_matches_pyproject,
    parse_package_release_tag,
    read_project_version,
)


class TestParsePackageReleaseTag:
    """Tests for :func:`parse_package_release_tag`."""

    def test_hyphenated_package_dir(self) -> None:
        """Parse version and directory with hyphens."""

        pep, pkg = parse_package_release_tag("v0.1.14-exdrf-gen-openapi2rtk")
        assert pep == "0.1.14"
        assert pkg == "exdrf-gen-openapi2rtk"

    def test_simple_name(self) -> None:
        """Parse a short package basename."""

        pep, pkg = parse_package_release_tag("v1.0.0-exdrf")
        assert pep == "1.0.0"
        assert pkg == "exdrf"

    def test_rejects_missing_suffix(self) -> None:
        """Tags without ``-<pkg>`` are invalid."""

        with pytest.raises(ValueError):
            parse_package_release_tag("v1.0.0")

    def test_rejects_path_segments_in_suffix(self) -> None:
        """Suffix must be a plain basename."""

        with pytest.raises(ValueError):
            parse_package_release_tag("v1.0.0-evil/../other")


class TestResolvePublishPackageDir:
    """Tests for :func:`resolve_publish_package_dir`."""

    def test_resolves_child_with_pyproject(self, tmp_path: Path) -> None:
        """Return the path when a child has ``pyproject.toml``."""

        nested = tmp_path / "exdrf-demo-pkg"
        nested.mkdir()
        (nested / "pyproject.toml").write_text(
            '[project]\nname = "demo"\nversion = "0.0.1"\n',
            encoding="utf-8",
        )
        got = resolve_publish_package_dir(tmp_path, "exdrf-demo-pkg")
        assert got == nested.resolve()

    def test_rejects_parent_escape(self, tmp_path: Path) -> None:
        """``..`` in the name is not allowed."""

        with pytest.raises(ValueError):
            resolve_publish_package_dir(tmp_path, "..")


class TestReadProjectVersion:
    """Tests for :func:`read_project_version`."""

    def test_reads_static_version(self, tmp_path: Path) -> None:
        """Read ``[project].version`` string."""

        manifest = tmp_path / "pyproject.toml"
        manifest.write_text(
            '[project]\nname = "x"\nversion = "2.3.4"\n',
            encoding="utf-8",
        )
        assert read_project_version(manifest) == "2.3.4"


class TestAssertReleaseVersionMatchesPyproject:
    """Tests for :func:`assert_release_version_matches_pyproject`."""

    def test_accepts_matching_version(self, tmp_path: Path) -> None:
        """No error when tag version matches ``pyproject.toml``."""

        pkg = tmp_path / "exdrf-match"
        pkg.mkdir()
        (pkg / "pyproject.toml").write_text(
            '[project]\nname = "match"\nversion = "1.2.3"\n',
            encoding="utf-8",
        )
        assert_release_version_matches_pyproject(tmp_path, "exdrf-match", "1.2.3")

    def test_rejects_mismatch(self, tmp_path: Path) -> None:
        """Raises when versions differ."""

        pkg = tmp_path / "exdrf-mismatch"
        pkg.mkdir()
        (pkg / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "1.0.0"\n',
            encoding="utf-8",
        )
        with pytest.raises(ValueError):
            assert_release_version_matches_pyproject(
                tmp_path,
                "exdrf-mismatch",
                "9.9.9",
            )
