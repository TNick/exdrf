"""Run pytest across multiple directories, continuing on failures."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence


@dataclass(frozen=True)
class DirResult:
    """Result of running pytest in one directory."""

    name: str
    exit_code: int


def _pythonpath_for_mono_repo(root: Path, all_dirs: Sequence[str]) -> str:
    """Build PYTHONPATH so every top-level package dir is importable.

    Each monorepo member lives under ``root/<dirname>`` (e.g. ``exdrf-al``).
    Putting only ``root`` on PYTHONPATH does not expose ``exdrf_al``; listing
    every package directory matches editable installs and keeps pytest runs
    consistent on Linux and Windows.

    Args:
        root: Repository root (parent of ``exdrf``, ``exdrf-al``, …).
        all_dirs: Directory names in install order (same as ``Makefile`` ``DIRS``).

    Returns:
        ``PYTHONPATH`` string for subprocess environments.
    """

    entries: list[str] = []
    for name in all_dirs:
        pkg_dir = (root / name).resolve()
        if pkg_dir.is_dir() and (pkg_dir / "pyproject.toml").is_file():
            entries.append(str(pkg_dir))
    if not entries:
        entries.append(str(root.resolve()))
    joined = os.pathsep.join(entries)
    existing = os.environ.get("PYTHONPATH", "")
    if not existing:
        return joined
    return joined + os.pathsep + existing


def run_pytest_in_dir(
    *,
    root: Path,
    directory: Path,
    all_dirs: Sequence[str],
    pytest_args: Sequence[str],
) -> DirResult:
    """Run pytest within one directory.

    Args:
        root: Workspace root used to build PYTHONPATH.
        directory: Directory to run pytest in.
        all_dirs: All package directory names under ``root`` (for PYTHONPATH).
        pytest_args: Extra args passed to pytest.

    Note:
        Always prepends ``-o asyncio_default_fixture_loop_scope=function`` so
        pytest-asyncio does not emit an unset-loop-scope deprecation warning.

    Returns:
        DirResult for the directory.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = _pythonpath_for_mono_repo(root, all_dirs)

    # Avoid pytest-asyncio deprecation about unset default fixture loop scope.
    asyncio_scope_opt = ["-o", "asyncio_default_fixture_loop_scope=function"]

    cmd = [sys.executable, "-m", "pytest", *asyncio_scope_opt, *pytest_args]
    proc = subprocess.run(
        cmd,
        cwd=str(directory),
        env=env,
        text=True,
    )
    return DirResult(name=directory.name, exit_code=int(proc.returncode))


def run_pytest_in_dirs(
    *,
    root: Path,
    dirs: Sequence[str],
    pytest_args: Sequence[str],
) -> int:
    """Run pytest across directories and return process exit code."""
    failures: List[DirResult] = []

    for d in dirs:
        d_path = (root / d).resolve()
        print(f"=== Running pytest in {d} ===", flush=True)

        if not d_path.exists():
            print(f"Skipping {d} - directory not found", flush=True)
            continue

        try:
            result = run_pytest_in_dir(
                root=root,
                directory=d_path,
                all_dirs=list(dirs),
                pytest_args=pytest_args,
            )
        except FileNotFoundError:
            print(
                "ERROR: pytest not found on PATH. "
                "Activate your venv and ensure pytest is installed.",
                file=sys.stderr,
                flush=True,
            )
            return 2

        if result.exit_code == 0:
            continue
        if result.exit_code == 5:
            print(f"No tests in {d} - skipping", flush=True)
            continue

        print(f"Tests FAILED in {d} (exit {result.exit_code})", flush=True)
        failures.append(result)

    if failures:
        failed_dirs = " ".join(r.name for r in failures)
        print(
            f"One or more directories had failing tests: {failed_dirs}",
            file=sys.stderr,
            flush=True,
        )
        return 1
    return 0


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run pytest per directory and continue on failure."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Workspace root for PYTHONPATH and directory resolution.",
    )
    parser.add_argument(
        "--pytest-args",
        nargs=argparse.REMAINDER,
        default=None,
        help=(
            "Extra arguments passed to pytest. "
            "Place this option last so all remaining tokens are forwarded."
        ),
    )
    parser.add_argument(
        "dirs",
        nargs="+",
        help="Directories (relative to root) to run pytest in.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)
    root = Path(args.root).resolve()
    pytest_args = list(args.pytest_args or [])

    # Strip optional separator marker when caller passes ``--pytest-args -- ...``.
    if pytest_args and pytest_args[0] == "--":
        pytest_args = pytest_args[1:]

    return run_pytest_in_dirs(
        root=root,
        dirs=list(args.dirs),
        pytest_args=pytest_args,
    )


if __name__ == "__main__":
    raise SystemExit(main())
