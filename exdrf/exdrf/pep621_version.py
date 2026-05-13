"""Resolve PEP 621 ``[project].version``, preferring a sibling
``pyproject.toml``.
"""

from __future__ import annotations

import importlib.metadata
import logging
import re
from pathlib import Path

import tomllib

logger = logging.getLogger(__name__)


def distribution_version(dist_name: str, pyproject_path: Path) -> str:
    """Return this distribution's version string.

    When ``pyproject.toml`` is present next to the importable package (source
    tree or editable install), ``[project].version`` is authoritative so a stray
    older wheel in the environment does not mask the checkout. Wheels normally
    omit that file under ``site-packages``, so installed releases use
    ``importlib.metadata`` instead.

    Args:
        dist_name: ``project.name`` from that project's ``pyproject.toml``.
        pyproject_path: Path to ``pyproject.toml`` next to the package
            directory.

    Returns:
        Non-empty version string.

    Raises:
        KeyError: When TOML has no static ``project.version``.
        TypeError: When ``project.version`` is not a string.
        importlib.metadata.PackageNotFoundError: When no TOML is available and
            the distribution is not installed.
    """

    # Prefer the sibling pyproject.toml from a checkout or editable layout.
    if pyproject_path.is_file():
        raw = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        project = raw.get("project")
        if not isinstance(project, dict):
            raise KeyError("project.version")
        if project.get("name") == dist_name:
            ver = project.get("version")
            if ver is None:
                raise KeyError("project.version")
            if not isinstance(ver, str):
                raise TypeError("project.version must be str")
            return ver
        logger.log(
            1,
            "project.name in %s does not match %s; using importlib.metadata",
            pyproject_path,
            dist_name,
        )

    try:
        return importlib.metadata.version(dist_name)
    except importlib.metadata.PackageNotFoundError:
        logger.error(
            "No usable pyproject at %s and distribution %s is not installed",
            pyproject_path,
            dist_name,
            exc_info=True,
        )
        raise


def version_tuple_from_string(version: str) -> tuple[int | str, ...]:
    """Split a PEP 440-ish version string into a tuple.

    Intended for CLI/UI parity with historic setuptools-scm tuples. Segments
    are split on ``.`` and ``-``; purely numeric segments become ``int``.

    Args:
        version: Version string such as ``0.1.23`` or ``0.1.0-dev``.

    Returns:
        Tuple of ints and/or non-numeric segment strings.

    Raises:
        ValueError: When ``version`` is empty after splitting.
    """

    parts = [p for p in re.split(r"[-.]", version) if p]
    if not parts:
        raise ValueError("empty version tuple")

    out: list[int | str] = []
    for segment in parts:
        if segment.isdigit():
            out.append(int(segment))
        else:
            out.append(segment)
    return tuple(out)
