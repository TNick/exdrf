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


def _py_path_with_root(root: Path) -> str:
    """Prepend root to PYTHONPATH in an OS-correct way."""
    root_str = str(root)
    existing = os.environ.get("PYTHONPATH", "")
    if not existing:
        return root_str
    return root_str + os.pathsep + existing


def run_pytest_in_dir(
    *,
    root: Path,
    directory: Path,
    pytest_args: Sequence[str],
) -> DirResult:
    """Run pytest within one directory.

    Args:
        root: Workspace root for PYTHONPATH.
        directory: Directory to run pytest in.
        pytest_args: Extra args passed to pytest.

    Returns:
        DirResult for the directory.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = _py_path_with_root(root)

    cmd = [sys.executable, "-m", "pytest", *pytest_args]
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
        nargs="*",
        default=[],
        help="Extra arguments passed to pytest.",
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
    return run_pytest_in_dirs(
        root=root, dirs=list(args.dirs), pytest_args=list(args.pytest_args)
    )


if __name__ == "__main__":
    raise SystemExit(main())
