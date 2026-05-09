"""Run mypy across monorepo directories with a strict error budget gate."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence

SUMMARY_RE = re.compile(r"Found (?P<count>\d+) errors? in \d+ files")


def _pythonpath_for_mono_repo(root: Path, dirs: Sequence[str]) -> str:
    """Build PYTHONPATH with all package directories.

    Args:
        root: Monorepo root directory.
        dirs: Package directories under the root.

    Returns:
        Combined PYTHONPATH value for mypy subprocesses.
    """

    entries: list[str] = []

    # Include each package path so cross-package imports resolve in mypy.
    for name in dirs:
        pkg_dir = (root / name).resolve()
        if pkg_dir.is_dir() and (pkg_dir / "pyproject.toml").is_file():
            entries.append(str(pkg_dir))

    # Fall back to repository root when no package directory is discovered.
    if not entries:
        entries.append(str(root.resolve()))

    joined = os.pathsep.join(entries)
    existing = os.environ.get("PYTHONPATH", "")
    if not existing:
        return joined
    return joined + os.pathsep + existing


def _run_mypy_in_dir(
    *,
    python_executable: str,
    root: Path,
    dir_name: str,
    all_dirs: Sequence[str],
) -> tuple[int, int]:
    """Run mypy in one directory and return detected errors.

    Args:
        python_executable: Python interpreter used to execute mypy.
        root: Monorepo root path.
        dir_name: Directory name under root where mypy runs.
        all_dirs: All package directories, used to build PYTHONPATH.

    Returns:
        A tuple of `(exit_code, error_count_from_summary_lines)`.
    """

    target_dir = (root / dir_name).resolve()
    if not target_dir.exists():
        print(f"Skipping {dir_name} - directory not found", flush=True)
        return 0, 0

    env = dict(os.environ)
    env["PYTHONPATH"] = _pythonpath_for_mono_repo(root, all_dirs)

    # Exclude generated UI files, setup scripts, and setuptools build trees that
    # duplicate package sources under ``build/lib/...``.
    cmd = [
        python_executable,
        "-m",
        "mypy",
        "--exclude",
        r"(^|\\|/)setup\.py$|_ui\.py$|(^|\\|/)build(\\|/)",
        ".",
    ]
    print(f"=== Running mypy in {dir_name} ===", flush=True)
    proc = subprocess.run(
        cmd,
        cwd=str(target_dir),
        env=env,
        text=True,
        capture_output=True,
    )

    output = proc.stdout + proc.stderr
    if output:
        print(output, end="")

    summary_errors = 0

    # Sum the canonical mypy summary lines so we can enforce a stable budget.
    for line in output.splitlines():
        match = SUMMARY_RE.search(line)
        if not match:
            continue
        summary_errors += int(match.group("count"))

    return int(proc.returncode), summary_errors


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        argv: Optional argument vector override.

    Returns:
        Parsed namespace.
    """

    parser = argparse.ArgumentParser(
        description="Run mypy over directories and enforce max error budget.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable used to run mypy.",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Workspace root for directory resolution and PYTHONPATH.",
    )
    parser.add_argument(
        "--max-errors",
        type=int,
        required=True,
        help="Maximum allowed aggregated mypy errors.",
    )
    parser.add_argument(
        "dirs",
        nargs="+",
        help="Directories to type-check.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Execute mypy checks and enforce the configured error budget.

    Args:
        argv: Optional command line argument override.

    Returns:
        Process exit code.
    """

    args = _parse_args(argv)
    root = Path(args.root).resolve()

    total_errors = 0
    non_zero_runs = 0

    # Run mypy for each package and aggregate summary counts.
    for dir_name in args.dirs:
        exit_code, found_errors = _run_mypy_in_dir(
            python_executable=args.python,
            root=root,
            dir_name=dir_name,
            all_dirs=args.dirs,
        )
        total_errors += found_errors
        if exit_code != 0:
            non_zero_runs += 1

    print(
        f"Mypy aggregated errors: {total_errors} (budget: {args.max_errors})",
        flush=True,
    )

    if total_errors > args.max_errors:
        print(
            f"ERROR: mypy error budget exceeded by {total_errors - args.max_errors}.",
            file=sys.stderr,
            flush=True,
        )
        return 1

    # Preserve signal that mypy ran and checked code paths in each package.
    if non_zero_runs > 0:
        print(
            "Mypy completed with existing errors inside budget.",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
