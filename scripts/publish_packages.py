"""Upload built wheels and sdists for every exdrf package using Twine."""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from exdrf_repo_paths import discover_package_dirs  # noqa: E402

logger = logging.getLogger(__name__)


def _artifacts(dist_dir: Path) -> list[Path]:
    """List wheel and sdist files under ``dist_dir``.

    Args:
        dist_dir: A package ``dist`` directory.

    Returns:
        Paths to ``.whl`` and ``.tar.gz`` files.
    """

    wheels = sorted(dist_dir.glob("*.whl"))
    tars = sorted(dist_dir.glob("*.tar.gz"))
    return wheels + tars


def main() -> None:
    """Parse CLI arguments and upload all artifacts with Twine."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root (default: parent of scripts/).",
    )
    parser.add_argument(
        "--repository",
        default="testpypi",
        help="Twine repository name (default: testpypi).",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Pass ``--non-interactive`` to Twine.",
    )
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=None,
        help=(
            "If set, upload all ``.whl`` and ``.tar.gz`` in this directory once "
            "instead of per-package ``dist/``."
        ),
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    repo_root = args.root
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent
    repo_root = repo_root.resolve()

    if args.artifacts_dir is not None:
        dist_dir = args.artifacts_dir.resolve()
        files = _artifacts(dist_dir)
        if not files:
            logger.error("No artifacts to upload in %s", dist_dir)
            raise SystemExit(1)
        upload_sets = [(dist_dir.name, files)]
    else:
        package_dirs = discover_package_dirs(repo_root)
        if not package_dirs:
            logger.error("No packages found under %s", repo_root)
            raise SystemExit(1)
        upload_sets = []
        for pkg in package_dirs:
            dist_dir = pkg / "dist"
            files = _artifacts(dist_dir)
            if not files:
                logger.error("No artifacts to upload in %s", dist_dir)
                raise SystemExit(1)
            upload_sets.append((pkg.name, files))

    for label, files in upload_sets:
        cmd = [
            sys.executable,
            "-m",
            "twine",
            "upload",
            "--repository",
            args.repository,
        ]
        if args.non_interactive:
            cmd.append("--non-interactive")
        cmd.extend(str(f) for f in files)

        logger.info("Uploading %d files from %s", len(files), label)
        proc = subprocess.run(cmd, check=False)
        if proc.returncode != 0:
            logger.error("twine upload failed for %s", label)
            raise SystemExit(proc.returncode)

    logger.info("Upload complete (%d twine run(s))", len(upload_sets))


if __name__ == "__main__":
    main()
