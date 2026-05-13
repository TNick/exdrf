"""Parse registry release tags and compare versions to ``pyproject.toml``."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import tomllib

logger = logging.getLogger(__name__)

# v1.2.3-exdrf or v0.1.0-exdrf-gen-openapi2rtk
_PACKAGE_RELEASE_TAG = re.compile(r"^v(\d+\.\d+\.\d+)-(.+)$")


def parse_package_release_tag(tag: str) -> tuple[str, str]:
    """Split a package release tag into PEP 440 version and directory name.

    Args:
        tag: Tag such as ``v1.2.3-exdrf`` or ``v0.1.0-exdrf-gen-al2qt``.

    Returns:
        ``(pep_version, pkg_dir)`` where ``pkg_dir`` is the top-level monorepo
        folder name.

    Raises:
        ValueError: If ``tag`` is not ``vMAJOR.MINOR.PATCH-<pkg_dir>``.
    """

    cleaned = tag.strip().replace("\r", "")
    m = _PACKAGE_RELEASE_TAG.fullmatch(cleaned)
    if not m:
        msg = "release tag must look like vMAJOR.MINOR.PATCH-<pkg_dir> (got %r)"
        logger.error(msg, tag)
        raise ValueError(msg % tag)

    pep_ver = m.group(1)
    pkg_dir = m.group(2).strip()
    if not pkg_dir or "/" in pkg_dir or "\\" in pkg_dir or ".." in pkg_dir:
        msg = "invalid package directory segment in tag %r"
        logger.error(msg, tag)
        raise ValueError(msg % tag)
    return pep_ver, pkg_dir


def read_project_version(pyproject_path: Path) -> str:
    """Return ``[project].version`` from a ``pyproject.toml`` file.

    Args:
        pyproject_path: Path to ``pyproject.toml``.

    Returns:
        Version string.

    Raises:
        ValueError: When the file has no static ``[project].version`` string.
    """

    raw = pyproject_path.read_text(encoding="utf-8")
    data = tomllib.loads(raw)
    project = data.get("project")
    if not isinstance(project, dict):
        msg = "Missing [project] in %s"
        logger.error(msg, pyproject_path)
        raise ValueError(msg % pyproject_path)

    version = project.get("version")
    if not isinstance(version, str) or not version.strip():
        msg = "Missing static [project].version in %s"
        logger.error(msg, pyproject_path)
        raise ValueError(msg % pyproject_path)
    return version.strip()


def assert_release_version_matches_pyproject(
    repo_root: Path,
    pkg_dir: str,
    expected_pep_version: str,
) -> None:
    """Exit the process if the package version does not match the release tag.

    Args:
        repo_root: Repository root.
        pkg_dir: Top-level package directory name.
        expected_pep_version: Numeric ``X.Y.Z`` from the tag (no prefix).

    Raises:
        ValueError: On mismatch between tag and ``pyproject.toml``.
        FileNotFoundError: If ``pyproject.toml`` is missing.
    """

    manifest = (repo_root / pkg_dir / "pyproject.toml").resolve()
    if not manifest.is_file():
        msg = "no pyproject.toml at %s"
        logger.error(msg, manifest)
        raise FileNotFoundError(msg % manifest)

    declared = read_project_version(manifest)
    if declared != expected_pep_version:
        msg = (
            "tag version %s does not match [project].version %s in %s "
            "(bump pyproject or fix the tag)"
        )
        logger.error(
            msg,
            expected_pep_version,
            declared,
            manifest,
        )
        raise ValueError(
            msg % (expected_pep_version, declared, manifest),
        )
