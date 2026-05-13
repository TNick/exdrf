"""CLI: ensure a release tag version matches ``[project].version``."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from release_tag import (  # noqa: E402
    assert_release_version_matches_pyproject,
    parse_package_release_tag,
)

logger = logging.getLogger(__name__)


def main() -> None:
    """Parse arguments and validate the tag against one package."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root (default: parent of scripts/).",
    )
    parser.add_argument(
        "--tag",
        required=True,
        help="Release tag (e.g. v1.2.3-exdrf).",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    repo_root = args.root
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent
    repo_root = repo_root.resolve()

    pep_ver, pkg_dir = parse_package_release_tag(args.tag)
    assert_release_version_matches_pyproject(repo_root, pkg_dir, pep_ver)
    logger.info(
        "Release tag %s matches %s/pyproject.toml version %s",
        args.tag.strip(),
        pkg_dir,
        pep_ver,
    )


if __name__ == "__main__":
    try:
        main()
    except (ValueError, FileNotFoundError) as exc:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
        logger.error("assert_release_version failed: %s", exc, exc_info=True)
        raise SystemExit(1) from exc
