"""Verify that published exdrf distributions install from a package index."""

from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import tomllib

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from exdrf_repo_paths import discover_package_dirs  # noqa: E402

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
    """Create a clean venv and pip-install all exdrf packages at one version."""

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
        help=(
            "Exact PEP 440 version for every distribution " "(example: 1.2.3)."
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
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    repo_root = args.root
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent
    repo_root = repo_root.resolve()

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
        proc_in = subprocess.run(install_cmd, check=False)
        if proc_in.returncode != 0:
            logger.error("pip install failed with code %s", proc_in.returncode)
            raise SystemExit(proc_in.returncode)

        proc_imp = subprocess.run(
            [str(py), "-c", "import exdrf"],
            check=False,
        )
        if proc_imp.returncode != 0:
            logger.error("Smoke import exdrf failed")
            raise SystemExit(proc_imp.returncode)

        logger.info("Verification succeeded in %s", venv_dir)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
