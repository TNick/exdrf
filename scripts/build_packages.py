"""Build sdist and wheel for exdrf monorepo packages (all or selected)."""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from exdrf_repo_paths import (  # noqa: E402
    discover_package_dirs,
    resolve_publish_package_dir,
)

logger = logging.getLogger(__name__)

# Setuptools defaults to a ``build/`` directory under the project, which shadows
# PyPI's ``build`` package on ``sys.path``. We redirect ``--build-base`` to a
# temporary directory outside the package tree (via PEP 517 ``--global-option``).
_LEGACY_SETTOOLS_DIRS = frozenset({"build", "_setuptools_staging"})


def _normalize_exclude(names: list[str]) -> frozenset[str]:
    """Strip whitespace from ``--exclude`` tokens.

    Args:
        names: Raw values from repeated ``--exclude`` CLI flags.

    Returns:
        Non-empty normalized package basenames to skip.
    """

    out: list[str] = []
    for raw in names:
        cleaned = raw.strip().replace("\r", "")
        if cleaned:
            out.append(cleaned)
    return frozenset(out)


def _normalize_include(names: list[str]) -> list[str]:
    """Normalize ``--include`` tokens, preserve order, drop duplicates.

    Args:
        names: Raw values from repeated ``--include`` CLI flags.

    Returns:
        Ordered unique basenames to build.
    """

    seen: set[str] = set()
    out: list[str] = []
    for raw in names:
        cleaned = raw.strip().replace("\r", "")
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        out.append(cleaned)
    return out


def _preclean_setuptools_output_dirs(package_dirs: list[Path]) -> None:
    """Remove setuptools staging trees under each package before building.

    Deletes the legacy default ``build/`` layout, any in-repo ``*_setuptools_staging``
    trees from older runs, and mangled ``prog__*`` paths produced by broken
    ``--build-base`` experiments.

    Args:
        package_dirs: Discovered package roots (each contains ``pyproject.toml``).
    """

    for pkg in package_dirs:
        for name in _LEGACY_SETTOOLS_DIRS:
            stale = pkg / name
            if stale.is_dir():
                logger.info("Removing setuptools output directory %s", stale)
                shutil.rmtree(stale)

        for stray in sorted(pkg.glob("*setuptools_staging*")):
            if stray.is_dir():
                logger.info("Removing stray setuptools staging directory %s", stray)
                shutil.rmtree(stray)

        for stray in sorted(pkg.glob("prog__*")):
            if stray.is_dir():
                logger.info("Removing stray setuptools path artifact %s", stray)
                shutil.rmtree(stray)


def _verify_pyproject_build_installed() -> None:
    """Abort early unless pyproject-build's package files exist under site-packages.

    A broken install can leave only ``build-*.dist-info`` while the ``build/``
    package directory is missing; ``import build`` then resolves to unrelated
    namespace paths (for example from editable installs), and ``python -m build``
    fails with ``No module named build.__main__``.

    Raises:
        SystemExit: When ``build/__main__.py`` is missing from ``purelib``.
    """

    purelib = Path(sysconfig.get_paths()["purelib"])
    main_py = purelib / "build" / "__main__.py"
    if main_py.is_file():
        return

    logger.error(
        "pyproject-build is missing under %s (expected %s). "
        "Repair with: pip install --force-reinstall --no-cache-dir build",
        purelib,
        main_py,
    )
    raise SystemExit(1)


def _run_build(package_dir: Path, repo_root: Path) -> None:
    """Clean ``dist/`` then run ``python -m build`` for one package.

    Args:
        package_dir: Path to a directory containing ``pyproject.toml``.
        repo_root: Repository root used as subprocess cwd so local ``build/`` dirs
            in sibling packages are not added ahead of site-packages (with ``-P``).
    """

    dist_dir = package_dir / "dist"
    if dist_dir.is_dir():
        shutil.rmtree(dist_dir)

    # Remove legacy setuptools output dirs if present (defense in depth).
    for name in _LEGACY_SETTOOLS_DIRS:
        stale = package_dir / name
        if stale.is_dir():
            shutil.rmtree(stale)

    for stray in package_dir.glob("*setuptools_staging*"):
        if stray.is_dir():
            shutil.rmtree(stray)

    for stray in package_dir.glob("prog__*"):
        if stray.is_dir():
            shutil.rmtree(stray)

    temp_base = tempfile.mkdtemp(prefix="exdrf_setuptools_")
    try:
        base_posix = Path(temp_base).resolve().as_posix()
        setuptools_cfg = {
            "--global-option": "build --build-base=%s" % (base_posix,),
        }

        # ``-P``: do not prepend cwd to sys.path (Python 3.11+). We pass an absolute
        # ``srcdir`` so pyproject-build still finds the project without shadowing.
        # ``--config-json`` sends setuptools' ``build`` command to a temp directory
        # so nothing named ``build`` appears under the package root.
        cmd = [
            sys.executable,
            "-P",
            "-m",
            "build",
            "--sdist",
            "--wheel",
            "--config-json",
            json.dumps(setuptools_cfg),
            str(package_dir.resolve()),
        ]
        logger.info("Building %s", package_dir)
        proc = subprocess.run(
            cmd,
            cwd=repo_root,
            check=False,
        )
        if proc.returncode != 0:
            logger.error(
                "build failed for %s with code %s", package_dir, proc.returncode
            )
            raise SystemExit(proc.returncode)
    finally:
        shutil.rmtree(temp_base, ignore_errors=True)


def _run_twine_check(package_dir: Path) -> None:
    """Run ``twine check`` on built artifacts under ``package_dir/dist``.

    Args:
        package_dir: Package directory whose ``dist/`` contains wheels/sdists.
    """

    dist_dir = package_dir / "dist"
    if not dist_dir.is_dir():
        logger.error("No dist directory after build: %s", dist_dir)
        raise SystemExit(1)

    cmd = [sys.executable, "-m", "twine", "check", str(dist_dir / "*")]
    # twine check does not expand globs on Windows the same way; pass explicit files.
    artifacts = sorted(dist_dir.glob("*.whl")) + sorted(dist_dir.glob("*.tar.gz"))
    if not artifacts:
        logger.error("No wheel or sdist in %s", dist_dir)
        raise SystemExit(1)

    cmd = [sys.executable, "-m", "twine", "check", *[str(a) for a in artifacts]]
    proc = subprocess.run(cmd, check=False)
    if proc.returncode != 0:
        logger.error("twine check failed for %s", package_dir)
        raise SystemExit(proc.returncode)


def main() -> None:
    """Parse CLI arguments and build discovered or selected packages."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root (default: parent of scripts/).",
    )
    parser.add_argument(
        "--skip-twine-check",
        action="store_true",
        help="Skip ``twine check`` after each build.",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="PKG",
        help=(
            "Skip one or more package directory basenames "
            "(e.g. ``exdrf-qt``). May be repeated."
        ),
    )
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        metavar="PKG",
        help=(
            "Build only these package directory basenames "
            "(e.g. ``exdrf`` or ``exdrf-al``). May be repeated."
        ),
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    repo_root = args.root
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent
    repo_root = repo_root.resolve()

    include_names = _normalize_include(args.include)
    skip = _normalize_exclude(args.exclude)
    if include_names and skip:
        logger.error("Use either --include or --exclude, not both")
        raise SystemExit(2)

    if include_names:
        package_dirs = [
            resolve_publish_package_dir(repo_root, n) for n in include_names
        ]
    else:
        package_dirs = [
            p for p in discover_package_dirs(repo_root) if p.name not in skip
        ]

    if not package_dirs:
        logger.error("No packages found under %s", repo_root)
        raise SystemExit(1)

    _preclean_setuptools_output_dirs(package_dirs)
    _verify_pyproject_build_installed()

    for pkg in package_dirs:
        _run_build(pkg, repo_root)
        if not args.skip_twine_check:
            _run_twine_check(pkg)

    logger.info("Built %d packages under %s", len(package_dirs), repo_root)


if __name__ == "__main__":
    main()
