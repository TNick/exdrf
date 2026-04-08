"""Pre-commit helper: delete stray empty regular files named exactly ``file``.

Typical accidental paths are repository-root ``file`` or ``some_pkg/file``
created by tooling or editor mistakes.

Usage:
  python -m exdrf_dev.remove_empty_file_named_file <path> ...

Removes only regular files whose final path component is ``file`` and whose
size is zero bytes.

Returns:
  Exit code ``0`` if nothing was removed, ``1`` if at least one file was
  removed (so pre-commit can interrupt and let the user re-stage), or ``2``
  if removal was attempted but failed with an OS error.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Iterable, List

logger = logging.getLogger(__name__)


def _is_empty_file_named_file(path: Path) -> bool:
    """Return True if ``path`` is a regular empty file named ``file``.

    Args:
        path: Candidate filesystem path (may be relative).

    Returns:
        True when the basename is exactly ``file``, the path exists as a
        regular file, and its size is zero bytes.
    """
    if path.name != "file":
        return False

    if not path.exists():
        return False

    if not path.is_file():
        return False

    try:
        return path.stat().st_size == 0
    except OSError as exc:
        logger.log(
            1,
            "could not stat path %s: %s",
            path,
            exc,
            exc_info=True,
        )
        return False


def remove_empty_file_named_file_paths(paths: Iterable[str]) -> List[Path]:
    """Remove empty files named ``file`` from the given path strings.

    Args:
        paths: Paths passed by pre-commit or the shell (deduplicated in
            encounter order).

    Returns:
        List of paths that were successfully removed.

    Raises:
        SystemExit: With code ``2`` if ``unlink`` fails for a path that
            should have been removed.
    """
    seen: dict[str, None] = {}
    unique_paths: List[Path] = []
    for raw in paths:
        if raw in seen:
            continue
        seen[raw] = None
        unique_paths.append(Path(raw))

    removed: List[Path] = []

    for path in unique_paths:
        path = path.resolve()

        if not _is_empty_file_named_file(path):
            continue

        try:
            path.unlink()
        except OSError as exc:
            logger.error(
                "could not remove stray empty file %s: %s",
                path,
                exc,
                exc_info=True,
            )
            print(
                "%s: could not remove stray empty file: %s" % (path, exc),
                file=sys.stderr,
            )
            raise SystemExit(2) from exc

        print("removed empty stray file: %s" % path)
        removed.append(path)

    return removed


def main(argv: List[str] | None = None) -> int:
    """Run removal for CLI arguments and return a process exit code.

    Args:
        argv: Arguments without the program name; defaults to
            ``sys.argv[1:]``.

    Returns:
        ``0`` if no file was removed, ``1`` if at least one was removed.
    """
    if argv is None:
        argv = sys.argv[1:]

    removed = remove_empty_file_named_file_paths(argv)
    return 1 if removed else 0


if __name__ == "__main__":
    raise SystemExit(main())
