"""Copy built wheels and sdists into a single directory for upload."""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from exdrf_repo_paths import (  # noqa: E402
    discover_package_dirs,
    resolve_publish_package_dir,
)

logger = logging.getLogger(__name__)


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
        Ordered unique basenames to collect from.
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
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="PKG",
        help="Skip one or more package directory basenames. May be repeated.",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        metavar="PKG",
        help="Collect only these package directory basenames. May be repeated.",
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
        logger.error("No packages selected under %s", repo_root)
        raise SystemExit(1)

    out_dir = args.out
    if out_dir is None:
        out_dir = repo_root / "release_dist"
    else:
        out_dir = out_dir.resolve()

    if out_dir.is_dir():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

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
