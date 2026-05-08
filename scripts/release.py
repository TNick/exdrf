"""Bump the tracked VERSION file, commit, tag ``v*``, and push to origin."""

from __future__ import annotations

import argparse
import logging
import re
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_VERSION_LINE = re.compile(r"^\s*(\d+)\.(\d+)\.(\d+)\s*$")


def _git(
    repo: Path,
    *args: str,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run ``git`` with ``cwd=repo``.

    Args:
        repo: Git repository root.
        args: Extra git arguments.
        capture: When True, capture stdout/stderr as text.

    Returns:
        Completed process result.
    """

    cmd = ["git", *args]
    return subprocess.run(
        cmd,
        cwd=repo,
        check=False,
        text=True,
        capture_output=capture,
    )


def _read_version(version_file: Path) -> tuple[int, int, int]:
    """Parse ``MAJOR.MINOR.PATCH`` from ``version_file``.

    Args:
        version_file: Path to the single-line VERSION file.

    Returns:
        Three-tuple of integers.

    Raises:
        ValueError: If the file does not contain a valid version line.
    """

    if not version_file.is_file():
        return (0, 0, 0)

    line = version_file.read_text(encoding="utf-8").splitlines()
    if not line:
        return (0, 0, 0)

    m = _VERSION_LINE.match(line[0])
    if not m:
        msg = "VERSION must be a single line MAJOR.MINOR.PATCH, got %r"
        logger.error(msg, line[0])
        raise ValueError(msg % line[0])
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def _bump(current: tuple[int, int, int], part: str) -> tuple[int, int, int]:
    """Increment ``current`` according to ``part``.

    Args:
        current: Current semantic version triple.
        part: One of ``patch``, ``minor``, ``major``.

    Returns:
        New semantic version triple.
    """

    major, minor, patch = current
    if part == "patch":
        return (major, minor, patch + 1)
    if part == "minor":
        return (major, minor + 1, 0)
    if part == "major":
        return (major + 1, 0, 0)
    msg = "Unknown bump part: %s"
    logger.error(msg, part)
    raise ValueError(msg % part)


def _latest_tag(repo: Path) -> str | None:
    """Return the latest ``v*`` tag name or None.

    Args:
        repo: Git repository root.

    Returns:
        Tag string such as ``v1.0.0`` or None if no tags match.
    """

    proc = _git(
        repo,
        "tag",
        "--list",
        "v*",
        "--sort=-v:refname",
        capture=True,
    )
    if proc.returncode != 0:
        logger.error("git tag list failed: %s", proc.stderr)
        raise SystemExit(proc.returncode)

    lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    return lines[0] if lines else None


def _parse_tag(tag: str) -> tuple[int, int, int]:
    """Parse ``vMAJOR.MINOR.PATCH`` into integers.

    Args:
        tag: Git tag string.

    Returns:
        Version triple.

    Raises:
        ValueError: If ``tag`` is not a valid ``v*`` semver tag.
    """

    if not tag.startswith("v"):
        msg = "Tag must start with v, got %r"
        raise ValueError(msg % tag)
    rest = tag[1:]
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", rest)
    if not m:
        msg = "Tag must be vMAJOR.MINOR.PATCH, got %r"
        raise ValueError(msg % tag)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def main() -> None:
    """Entry point for the release helper."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root (default: parent of scripts/).",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--set-version",
        help="Exact version to release (e.g. 1.2.3).",
    )
    group.add_argument(
        "--bump",
        choices=("patch", "minor", "major"),
        help="Increment VERSION (or latest v* tag) by patch, minor, or major.",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow a dirty working tree (not recommended).",
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Commit and tag locally without ``git push``.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    repo_root = args.root
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent
    repo_root = repo_root.resolve()

    version_file = repo_root / "VERSION"

    status = _git(repo_root, "status", "--porcelain", capture=True)
    if status.returncode != 0:
        logger.error("git status failed: %s", status.stderr)
        raise SystemExit(status.returncode)
    if status.stdout.strip() and not args.allow_dirty:
        logger.error(
            "Working tree is not clean; commit or stash changes first.",
        )
        raise SystemExit(1)

    if args.set_version is not None:
        m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", args.set_version.strip())
        if not m:
            logger.error("--set-version must be MAJOR.MINOR.PATCH")
            raise SystemExit(1)
        new_ver = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    else:
        file_ver = _read_version(version_file)
        tag_name = _latest_tag(repo_root)
        if file_ver != (0, 0, 0):
            base = file_ver
        elif tag_name is not None:
            base = _parse_tag(tag_name)
        else:
            base = (0, 0, 0)
        new_ver = _bump(base, args.bump)

    version_str = f"{new_ver[0]}.{new_ver[1]}.{new_ver[2]}"
    tag = f"v{version_str}"

    existing = _git(
        repo_root,
        "rev-parse",
        "-q",
        "--verify",
        f"refs/tags/{tag}",
        capture=True,
    )
    if existing.returncode == 0:
        logger.error("Tag %s already exists", tag)
        raise SystemExit(1)

    version_file.write_text(version_str + "\n", encoding="utf-8")

    add = _git(repo_root, "add", "VERSION")
    if add.returncode != 0:
        logger.error("git add failed")
        raise SystemExit(add.returncode)

    commit = _git(
        repo_root,
        "commit",
        "-m",
        f"chore: release {version_str}",
    )
    if commit.returncode != 0:
        logger.error("git commit failed (nothing to commit?)")
        raise SystemExit(commit.returncode)

    tag_proc = _git(
        repo_root,
        "tag",
        "-a",
        tag,
        "-m",
        f"release {version_str}",
    )
    if tag_proc.returncode != 0:
        logger.error("git tag failed")
        raise SystemExit(tag_proc.returncode)

    if not args.no_push:
        push_branch = _git(repo_root, "push", "origin", "HEAD")
        if push_branch.returncode != 0:
            logger.error("git push HEAD failed")
            raise SystemExit(push_branch.returncode)
        push_tag = _git(repo_root, "push", "origin", tag)
        if push_tag.returncode != 0:
            logger.error("git push tag failed")
            raise SystemExit(push_tag.returncode)

    logger.info("Released %s as tag %s", version_str, tag)


if __name__ == "__main__":
    main()
