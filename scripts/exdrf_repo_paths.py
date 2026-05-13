"""Discover top-level Python package directories in the exdrf monorepo."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

logger = logging.getLogger(__name__)


def resolve_publish_package_dir(repo_root: Path, name: str) -> Path:
    """Return the absolute path to one top-level package directory.

    The directory must lie directly under ``repo_root`` and contain
    ``pyproject.toml``. Names with path separators or parent segments are
    rejected.

    Args:
        repo_root: Absolute path to the exdrf repository root.
        name: Directory basename (e.g. ``exdrf`` or ``exdrf-gen-al2qt``).

    Returns:
        Resolved directory path.

    Raises:
        ValueError: When ``name`` is empty, hidden, or unsafe.
        FileNotFoundError: When ``repo_root`` is not a directory or there is no
            ``pyproject.toml`` at the resolved path.
    """

    cleaned = name.strip().replace("\r", "")
    if not cleaned or cleaned.startswith("."):
        msg = "package directory name must be non-empty and not hidden, got %r"
        logger.error(msg, name)
        raise ValueError(msg % name)

    if "/" in cleaned or "\\" in cleaned or ".." in cleaned:
        msg = "package directory name must be a single basename, got %r"
        logger.error(msg, name)
        raise ValueError(msg % name)

    if not repo_root.is_dir():
        msg = "repo_root is not a directory: %s"
        logger.error(msg, repo_root)
        raise FileNotFoundError(msg % repo_root)

    root = repo_root.resolve()
    candidate = (root / cleaned).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        msg = "package directory %r escapes repo root"
        logger.error(msg, cleaned)
        raise ValueError(msg % cleaned) from None

    manifest = candidate / "pyproject.toml"
    if not manifest.is_file():
        msg = "no pyproject.toml at %s"
        logger.error(msg, manifest)
        raise FileNotFoundError(msg % manifest)
    return candidate


def discover_package_dirs(repo_root: Path) -> list[Path]:
    """Return sorted paths to each directory under ``repo_root`` that has a
    ``pyproject.toml``.

    Skips hidden directories and common non-package folders.

    Args:
        repo_root: Absolute or resolved path to the exdrf repository root.

    Returns:
        Sorted list of package directory paths (each contains ``pyproject.toml``).
    """

    # Skip names that are never top-level installable packages in this repo.
    skip_names = frozenset(
        {
            ".git",
            ".github",
            ".idea",
            ".vscode",
            "venv",
            "venv-qt5",
            "venv-qt6",
            "playground",
            "legacy",
            "scripts",
            "build",
            "dist",
        }
    )

    if not repo_root.is_dir():
        msg = "repo_root is not a directory: %s"
        logger.error(msg, repo_root)
        raise FileNotFoundError(msg % repo_root)

    # Collect immediate child directories that declare a Python project.
    candidates: list[Path] = []
    for child in repo_root.iterdir():
        if not child.is_dir():
            continue
        if child.name.startswith("."):
            continue
        if child.name in skip_names:
            continue
        if (child / "pyproject.toml").is_file():
            candidates.append(child)

    candidates.sort(key=lambda p: p.name.lower())
    return candidates


def package_dirs_from_makefile_order(
    repo_root: Path, ordered_names: Sequence[str]
) -> list[Path]:
    """Resolve ``ordered_names`` to existing package paths under ``repo_root``.

    Args:
        repo_root: Repository root.
        ordered_names: Directory names relative to ``repo_root`` (e.g. ``exdrf``).

    Returns:
        Paths in the same order as ``ordered_names`` where ``pyproject.toml``
        exists.

    Raises:
        FileNotFoundError: If any name does not resolve to a package directory.
    """

    resolved: list[Path] = []
    for name in ordered_names:
        path = repo_root / name
        if not (path / "pyproject.toml").is_file():
            msg = "Missing pyproject.toml for package dir %s"
            logger.error(msg, path)
            raise FileNotFoundError(msg % path)
        resolved.append(path)
    return resolved
