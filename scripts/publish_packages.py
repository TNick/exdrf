"""Upload built wheels and sdists for every exdrf package using Twine."""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

from packaging.utils import (
    InvalidSdistFilename,
    InvalidWheelFilename,
    parse_sdist_filename,
    parse_wheel_filename,
)
from packaging.version import Version

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from exdrf_repo_paths import discover_package_dirs  # noqa: E402

logger = logging.getLogger(__name__)


def _maybe_load_dotenv(repo_root: Path) -> None:
    """Load ``.env`` from the repository root so Twine can read credentials.

    Expects ``TWINE_USERNAME`` (often ``__token__``) and ``TWINE_PASSWORD`` (the
    PyPI API token value). If ``python-dotenv`` is not installed, does nothing.

    Args:
        repo_root: Root of the exdrf monorepo.
    """

    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    env_path = repo_root / ".env"
    if env_path.is_file():
        load_dotenv(env_path)


def _artifacts(dist_dir: Path) -> list[Path]:
    """List wheel and sdist files under ``dist_dir``.

    Args:
        dist_dir: A package ``dist`` directory.

    Returns:
        Paths to ``.whl`` and ``.tar.gz`` files.
    """

    wheels = sorted(dist_dir.glob("*.whl"))
    tars = sorted(dist_dir.glob("*.tar.gz"))
    return wheels + tars


def _version_from_artifact(artifact: Path) -> Version | None:
    """Return the PEP 440 ``Version`` parsed from an artifact filename.

    Args:
        artifact: Path to a built wheel (``.whl``) or sdist (``.tar.gz``).

    Returns:
        Parsed ``Version`` instance, or ``None`` when the filename does not
        match either format.
    """

    name = artifact.name
    if name.endswith(".whl"):
        try:
            _dist, version, _build, _tags = parse_wheel_filename(name)
        except InvalidWheelFilename:
            logger.log(1, "Skipping unparseable wheel %s", name, exc_info=True)
            return None
        return version
    if name.endswith(".tar.gz"):
        try:
            _dist, version = parse_sdist_filename(name)
        except InvalidSdistFilename:
            logger.log(1, "Skipping unparseable sdist %s", name, exc_info=True)
            return None
        return version
    return None


def _local_version_artifacts(files: list[Path]) -> list[tuple[Path, Version]]:
    """Return artifacts whose version contains a PEP 440 ``+local`` segment.

    PyPI and TestPyPI reject local versions (see PEP 440 and
    https://packaging.python.org/en/latest/specifications/version-specifiers/
    #local-version-identifiers). ``setuptools_scm`` produces such versions
    whenever ``HEAD`` is not exactly at a release tag or the tree is dirty.

    Args:
        files: Built artifacts about to be uploaded.

    Returns:
        List of ``(path, version)`` pairs for artifacts with a non-empty
        ``Version.local`` attribute.
    """

    bad: list[tuple[Path, Version]] = []
    for f in files:
        version = _version_from_artifact(f)
        if version is not None and version.local:
            bad.append((f, version))
    return bad


def main() -> None:
    """Parse CLI arguments and upload all artifacts with Twine."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root (default: parent of scripts/).",
    )
    parser.add_argument(
        "--repository",
        default="testpypi",
        help="Twine repository name (default: testpypi).",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Pass ``--non-interactive`` to Twine.",
    )
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=None,
        help=(
            "If set, upload all ``.whl`` and ``.tar.gz`` in this directory once "
            "instead of per-package ``dist/``."
        ),
    )
    parser.add_argument(
        "--allow-local-version",
        action="store_true",
        help=(
            "Allow uploading artifacts whose version contains a PEP 440 "
            "``+local`` identifier. By default such uploads are refused "
            "because PyPI and TestPyPI reject local versions; this flag "
            "exists for debugging mirrors that accept them."
        ),
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    repo_root = args.root
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent
    repo_root = repo_root.resolve()

    _maybe_load_dotenv(repo_root)

    if args.artifacts_dir is not None:
        dist_dir = args.artifacts_dir.resolve()
        files = _artifacts(dist_dir)
        if not files:
            logger.error("No artifacts to upload in %s", dist_dir)
            raise SystemExit(1)
        upload_sets = [(dist_dir.name, files)]
    else:
        package_dirs = discover_package_dirs(repo_root)
        if not package_dirs:
            logger.error("No packages found under %s", repo_root)
            raise SystemExit(1)
        upload_sets = []
        for pkg in package_dirs:
            dist_dir = pkg / "dist"
            files = _artifacts(dist_dir)
            if not files:
                logger.error("No artifacts to upload in %s", dist_dir)
                raise SystemExit(1)
            upload_sets.append((pkg.name, files))

    # Refuse PEP 440 ``+local`` versions early; PyPI/TestPyPI reject them at
    # upload time, so failing here saves a slow doomed twine round-trip.
    if not args.allow_local_version:
        all_files = [f for _, files in upload_sets for f in files]
        bad = _local_version_artifacts(all_files)
        if bad:
            bad_versions = sorted({str(v) for _, v in bad})
            logger.error(
                "Refusing to upload artifacts with PEP 440 local version "
                "identifiers (forbidden by PyPI/TestPyPI): %s",
                ", ".join(bad_versions),
            )
            logger.error(
                "Tag a real release first (e.g. ``make release "
                'EXDRF_RELEASE_ARGS="--bump patch"``) and rebuild, or pass '
                "``--allow-local-version`` to override.",
            )
            for path, version in bad:
                logger.error("  %s -> %s", path.name, version)
            raise SystemExit(1)

    for label, files in upload_sets:
        cmd = [
            sys.executable,
            "-m",
            "twine",
            "upload",
            "--verbose",
            "--repository",
            args.repository,
        ]
        if args.non_interactive:
            cmd.append("--non-interactive")
        cmd.extend(str(f) for f in files)

        logger.info("Uploading %d files from %s", len(files), label)
        proc = subprocess.run(cmd, check=False)
        if proc.returncode != 0:
            logger.error("twine upload failed for %s", label)
            raise SystemExit(proc.returncode)

    logger.info("Upload complete (%d twine run(s))", len(upload_sets))


if __name__ == "__main__":
    main()
