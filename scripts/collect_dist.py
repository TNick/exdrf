"""Copy all built wheels and sdists into a single directory for upload."""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from exdrf_repo_paths import discover_package_dirs  # noqa: E402

logger = logging.getLogger(__name__)


def main() -> None:
    """Copy artifacts from each ``<pkg>/dist`` into ``release_dist/``."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root (default: parent of scripts/).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory (default: <root>/release_dist).",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    repo_root = args.root
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent
    repo_root = repo_root.resolve()

    out_dir = args.out
    if out_dir is None:
        out_dir = repo_root / "release_dist"
    else:
        out_dir = out_dir.resolve()

    if out_dir.is_dir():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    package_dirs = discover_package_dirs(repo_root)
    copied = 0
    for pkg in package_dirs:
        dist_dir = pkg / "dist"
        if not dist_dir.is_dir():
            logger.error("Missing dist for %s; run build first", pkg.name)
            raise SystemExit(1)
        for artifact in sorted(dist_dir.glob("*.whl")) + sorted(
            dist_dir.glob("*.tar.gz")
        ):
            dest = out_dir / artifact.name
            if dest.exists():
                msg = "Duplicate artifact name %s"
                logger.error(msg, artifact.name)
                raise SystemExit(1)
            shutil.copy2(artifact, dest)
            copied += 1

    logger.info("Copied %d artifacts to %s", copied, out_dir)


if __name__ == "__main__":
    main()
