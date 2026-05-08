"""Build, validate, upload to TestPyPI, and verify installs (release rehearsal)."""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from built_version import version_from_any_wheel  # noqa: E402

logger = logging.getLogger(__name__)


def _run(script: str, extra: list[str]) -> None:
    """Run another script module in the same interpreter.

    Args:
        script: Basename under ``scripts/`` (e.g. ``build_packages.py``).
        extra: Additional argv tokens after the script path.
    """

    path = _SCRIPTS_DIR / script
    cmd = [sys.executable, str(path), *extra]
    logger.info("Running %s", " ".join(cmd))
    proc = subprocess.run(cmd, check=False)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def main() -> None:
    """Orchestrate build, twine upload to TestPyPI, and verify_install."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root (default: parent of scripts/).",
    )
    parser.add_argument(
        "--version",
        default=None,
        help=(
            "Version string matching TestPyPI artifacts (default: first line of "
            "VERSION in repo root)."
        ),
    )
    parser.add_argument(
        "--repository",
        default="testpypi",
        help="Twine repository name (default: testpypi).",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    root_args: list[str] = []
    if args.root is not None:
        root_args.extend(["--root", str(args.root.resolve())])

    _run("build_packages.py", root_args)
    _run("collect_dist.py", root_args)

    repo = args.root
    if repo is None:
        repo = Path(__file__).resolve().parent.parent
    repo = repo.resolve()

    if args.version is not None:
        version = args.version.strip()
    else:
        version = version_from_any_wheel(repo)
        logger.info("Detected built version from wheels: %s", version)
    merged_args = list(root_args)
    root = args.root
    if root is None:
        root = Path(__file__).resolve().parent.parent
    merged_args.extend(
        [
            "--artifacts-dir",
            str((root.resolve() / "release_dist")),
        ]
    )
    _run(
        "publish_packages.py",
        [
            *merged_args,
            "--repository",
            args.repository,
            "--non-interactive",
        ],
    )
    _run(
        "verify_install.py",
        [
            *root_args,
            "--version",
            version,
        ],
    )
    logger.info("fake-publish completed for version %s", version)


if __name__ == "__main__":
    main()
