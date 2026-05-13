"""Package version from PEP 621 or installed metadata."""

from __future__ import annotations

from pathlib import Path

from exdrf.pep621_version import distribution_version, version_tuple_from_string

_PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"
_DIST_NAME = "exdrf_xl"

__version__ = version = distribution_version(_DIST_NAME, _PYPROJECT)
__version_tuple__ = version_tuple = version_tuple_from_string(__version__)

__commit_id__ = commit_id = None

__all__ = [
    "__version__",
    "__version_tuple__",
    "version",
    "version_tuple",
    "__commit_id__",
    "commit_id",
]
