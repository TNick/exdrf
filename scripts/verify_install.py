"""Verify that published exdrf distributions install from a package index.

With ``--package-dir``, only that workspace package is installed and checked
via :func:`importlib.metadata.version`.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import tomllib

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from exdrf_repo_paths import (  # noqa: E402
    discover_package_dirs,
    resolve_publish_package_dir,
)

logger = logging.getLogger(__name__)


def _project_name(pyproject_path: Path) -> str:
    """Read ``[project].name`` from a ``pyproject.toml`` file.

    Args:
        pyproject_path: Path to ``pyproject.toml``.

    Returns:
        The normalized project name string.
    """

    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = data.get("project")
    if not isinstance(project, dict):
        msg = "Missing [project] in %s"
        logger.error(msg, pyproject_path)
        raise ValueError(msg % pyproject_path)
    name = project.get("name")
    if not isinstance(name, str) or not name.strip():
        msg = "Missing [project].name in %s"
        logger.error(msg, pyproject_path)
        raise ValueError(msg % pyproject_path)
    return name


def main() -> None:
    """Create a clean venv and pip-install packages, then smoke-check."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root (default: parent of scripts/).",
    )
    parser.add_argument(
        "--version",
        required=True,
        help=("Exact PEP 440 version for every distribution (example: 1.2.3)."),
    )
    parser.add_argument(
        "--package-dir",
        default=None,
        help=(
            "Top-level monorepo directory (e.g. exdrf-qt). When set, install "
            "only that project's [project].name at --version and verify metadata."
        ),
    )
    parser.add_argument(
        "--index-url",
        default="https://test.pypi.org/simple/",
        help="Primary index URL (default: TestPyPI).",
    )
    parser.add_argument(
        "--extra-index-url",
        default="https://pypi.org/simple/",
        help="Extra index URL for transitive dependencies (default: PyPI).",
    )
    parser.add_argument(
        "--install-attempts",
        type=int,
        default=1,
        metavar="N",
        help=(
            "Retry ``pip install`` up to N times (TestPyPI often lags right "
            "after upload). Default: 1 (no retries)."
        ),
    )
    parser.add_argument(
        "--install-retry-delay-seconds",
        type=int,
        default=15,
        metavar="SEC",
        help="Wait SEC seconds between pip install attempts (default: 15).",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    repo_root = args.root
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent
    repo_root = repo_root.resolve()

    if args.package_dir:
        pkg_root = resolve_publish_package_dir(repo_root, args.package_dir)
        names = [_project_name(pkg_root / "pyproject.toml")]
    else:
        package_dirs = discover_package_dirs(repo_root)
        names = [_project_name(p / "pyproject.toml") for p in package_dirs]
    specs = [f"{n}=={args.version}" for n in names]

    tmp = Path(tempfile.mkdtemp(prefix="exdrf-verify-"))
    venv_dir = tmp / "venv"
    try:
        proc_venv = subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            check=False,
        )
        if proc_venv.returncode != 0:
            logger.error(
                "venv creation failed with code %s",
                proc_venv.returncode,
            )
            raise SystemExit(proc_venv.returncode)

        if sys.platform == "win32":
            pip = venv_dir / "Scripts" / "pip.exe"
            py = venv_dir / "Scripts" / "python.exe"
        else:
            pip = venv_dir / "bin" / "pip"
            py = venv_dir / "bin" / "python"

        upgrade_cmd = [
            str(pip),
            "install",
            "-U",
            "pip",
            "setuptools",
            "wheel",
        ]
        proc_up = subprocess.run(upgrade_cmd, check=False)
        if proc_up.returncode != 0:
            logger.error("pip upgrade failed with code %s", proc_up.returncode)
            raise SystemExit(proc_up.returncode)

        install_cmd = [
            str(pip),
            "install",
            "--index-url",
            args.index_url,
            "--extra-index-url",
            args.extra_index_url,
        ]
        install_cmd.extend(specs)
        logger.info("Installing %d packages at ==%s", len(specs), args.version)

        proc_in: subprocess.CompletedProcess[str] | None = None
        for attempt in range(1, args.install_attempts + 1):
            proc_in = subprocess.run(install_cmd, check=False)
            if proc_in.returncode == 0:
                break
            logger.warning(
                "pip install attempt %d/%d failed with code %s",
                attempt,
                args.install_attempts,
                proc_in.returncode,
            )
            if attempt < args.install_attempts:
                logger.info(
                    "Retrying pip install in %d s (index may lag after upload)",
                    args.install_retry_delay_seconds,
                )
                time.sleep(args.install_retry_delay_seconds)
        else:
            logger.error(
                "pip install failed after %d attempt(s)",
                args.install_attempts,
            )
            raise SystemExit(proc_in.returncode if proc_in else 1)

        if args.package_dir:
            check_src = (
                "import importlib.metadata as m\n"
                "n = %r\n"
                "expected = %r\n"
                "got = m.version(n)\n"
                "assert got == expected, (n, got, expected)\n"
            ) % (names[0], args.version)
        else:
            check_src = "import exdrf"

        proc_imp = subprocess.run(
            [str(py), "-c", check_src],
            check=False,
        )
        if proc_imp.returncode != 0:
            logger.error(
                "Post-install verification failed with code %s",
                proc_imp.returncode,
            )
            raise SystemExit(proc_imp.returncode)

        logger.info("Verification succeeded in %s", venv_dir)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
