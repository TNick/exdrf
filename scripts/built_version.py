"""Read the distribution version from a freshly built wheel."""

from __future__ import annotations

import email.parser
import logging
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)


def version_from_any_wheel(repo_root: Path) -> str:
    """Return ``Version`` from the first ``.whl`` under any package ``dist/``.

    Args:
        repo_root: Repository root containing package subdirectories.

    Returns:
        PEP 440 version string from wheel metadata.

    Raises:
        FileNotFoundError: If no wheel is found.
        ValueError: If metadata has no Version field.
    """

    wheels: list[Path] = []
    for child in sorted(repo_root.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir():
            continue
        dist_dir = child / "dist"
        if not dist_dir.is_dir():
            continue
        wheels.extend(sorted(dist_dir.glob("*.whl")))

    if not wheels:
        msg = "No wheels found under any package dist/"
        logger.error(msg)
        raise FileNotFoundError(msg)

    wheel_path = wheels[0]
    with zipfile.ZipFile(wheel_path, "r") as zf:
        names = zf.namelist()
        meta_name = next(
            (n for n in names if n.endswith(".dist-info/METADATA")),
            None,
        )
        if meta_name is None:
            msg = "No METADATA in wheel %s"
            logger.error(msg, wheel_path)
            raise ValueError(msg % wheel_path)
        raw = zf.read(meta_name).decode("utf-8")

    parsed = email.parser.Parser().parsestr(raw)
    version = parsed.get("Version")
    if not version:
        msg_err = "METADATA missing Version in %s"
        logger.error(msg_err, wheel_path)
        raise ValueError(msg_err % wheel_path)
    return version.strip()


def main() -> None:
    """Print the version read from the first wheel under the repository."""

    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root (default: parent of scripts/).",
    )
    args = parser.parse_args()

    root = args.root
    if root is None:
        root = Path(__file__).resolve().parent.parent
    root = root.resolve()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    print(version_from_any_wheel(root), end="")


if __name__ == "__main__":
    main()
