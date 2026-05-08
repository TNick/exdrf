"""Build sdist and wheel for every exdrf monorepo package."""

from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from exdrf_repo_paths import discover_package_dirs  # noqa: E402

logger = logging.getLogger(__name__)


def _run_build(package_dir: Path) -> None:
    """Clean ``dist/`` then run ``python -m build`` for one package.

    Args:
        package_dir: Path to a directory containing ``pyproject.toml``.
    """

    dist_dir = package_dir / "dist"
    if dist_dir.is_dir():
        shutil.rmtree(dist_dir)

    cmd = [sys.executable, "-m", "build", "--sdist", "--wheel", "."]
    logger.info("Building %s", package_dir)
    proc = subprocess.run(
        cmd,
        cwd=package_dir,
        check=False,
    )
    if proc.returncode != 0:
        logger.error(
            "build failed for %s with code %s", package_dir, proc.returncode
        )
        raise SystemExit(proc.returncode)


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
    artifacts = sorted(dist_dir.glob("*.whl")) + sorted(
        dist_dir.glob("*.tar.gz")
    )
    if not artifacts:
        logger.error("No wheel or sdist in %s", dist_dir)
        raise SystemExit(1)

    cmd = [sys.executable, "-m", "twine", "check", *[str(a) for a in artifacts]]
    proc = subprocess.run(cmd, check=False)
    if proc.returncode != 0:
        logger.error("twine check failed for %s", package_dir)
        raise SystemExit(proc.returncode)


def main() -> None:
    """Parse CLI arguments and build every discovered package."""

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
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    repo_root = args.root
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent
    repo_root = repo_root.resolve()

    package_dirs = discover_package_dirs(repo_root)
    if not package_dirs:
        logger.error("No packages found under %s", repo_root)
        raise SystemExit(1)

    for pkg in package_dirs:
        _run_build(pkg)
        if not args.skip_twine_check:
            _run_twine_check(pkg)

    logger.info("Built %d packages under %s", len(package_dirs), repo_root)


if __name__ == "__main__":
    main()
