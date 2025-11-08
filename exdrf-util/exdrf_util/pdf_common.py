"""PDF utilities: font location, download, and registration.

This module provides a helper to ensure the DejaVu Serif (Condensed preferred)
font family is available for ReportLab and properly registered so that
bold/italic mappings work with ``<b>``, ``<i>`` and with TableStyle FONTNAME.
"""

from __future__ import annotations

import logging
import os
import platform
import urllib.request
import zipfile
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger(__name__)


#
# Constants
#

DEJAVU_VERSION = "version_2_37"
ZIP_URL = (
    "https://github.com/dejavu-fonts/dejavu-fonts/releases/download/"
    f"{DEJAVU_VERSION}/dejavu-fonts-ttf-2.37.zip"
)

# Minimal set of filenames we use; prefer Condensed first
DEJAVU_SERIF_CONDENSED: Dict[str, str] = {
    "normal": "DejaVuSerifCondensed.ttf",
    "bold": "DejaVuSerifCondensed-Bold.ttf",
    "italic": "DejaVuSerifCondensed-Italic.ttf",
    "boldItalic": "DejaVuSerifCondensed-BoldItalic.ttf",
}

DEJAVU_SERIF: Dict[str, str] = {
    "normal": "DejaVuSerif.ttf",
    "bold": "DejaVuSerif-Bold.ttf",
    "italic": "DejaVuSerif-Italic.ttf",
    "boldItalic": "DejaVuSerif-BoldItalic.ttf",
}


@dataclass
class FontPaths:
    """Resolved paths for a font family.

    Attributes:
        normal: Regular style path.
        bold: Bold style path.
        italic: Italic style path.
        boldItalic: Bold-italic style path.
    """

    normal: str
    bold: str
    italic: str
    boldItalic: str


def _read_env_path() -> Optional[str]:
    """Return path from EXDRF_TTF_DIR if set and exists."""

    value = os.environ.get("EXDRF_TTF_DIR")
    if value and os.path.isdir(value):
        return value
    return None


def _user_data_dir_fallback(app_name: str) -> str:
    """Return a reasonable per-user app data directory without appdirs.

    This attempts OS-specific conventions similar to appdirs.user_data_dir.
    """

    system = platform.system().lower()

    # Windows: LOCALAPPDATA preferred, fallback to APPDATA
    if system == "windows":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if not base:
            base = os.path.expanduser("~\\AppData\\Local")
        return os.path.join(base, app_name)

    # macOS
    if system == "darwin":
        return os.path.join(
            os.path.expanduser("~/Library/Application Support"), app_name
        )

    # Linux and others follow XDG_DATA_HOME
    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser(
        "~/.local/share"
    )
    return os.path.join(base, app_name)


def _user_data_dir(app_name: str, app_author: str) -> str:
    """Return user data directory; prefer appdirs if available."""

    try:
        import appdirs  # type: ignore

        return appdirs.user_data_dir(appname=app_name, appauthor=app_author)
    except Exception:
        return _user_data_dir_fallback(app_name)


def _fonts_dir() -> str:
    """Return the directory where we cache TTFs for this app.

    The directory is created if it does not exist.
    """

    # Prefer explicit env var if provided
    env_dir = _read_env_path()
    if env_dir:
        path = os.path.abspath(env_dir)
    else:
        # Use a generic vendor/app pair; stable across this codebase
        base = _user_data_dir(app_name="exdrf", app_author="exdrf")
        path = os.path.join(base, "fonts")

    os.makedirs(path, exist_ok=True)
    return path


def _download_file(url: str, dest_path: str, timeout: float = 20.0) -> None:
    """Download a file to a destination path.

    Overwrites existing file if present and size is zero; otherwise leaves it.
    """

    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        return

    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = resp.read()
        if not data:
            raise OSError("empty download")
        with open(dest_path, "wb") as fh:
            fh.write(data)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to download font from %s: %s", url, exc)
        raise


def _ensure_zip_downloaded(zip_path: str) -> None:
    """Ensure the DejaVu TTF zip exists locally, downloading if missing."""

    if os.path.exists(zip_path) and os.path.getsize(zip_path) > 0:
        return

    tmp_path = f"{zip_path}.part"
    try:
        with urllib.request.urlopen(ZIP_URL, timeout=40.0) as resp:
            data = resp.read()
        if not data:
            raise OSError("empty download")
        with open(tmp_path, "wb") as fh:
            fh.write(data)
        os.replace(tmp_path, zip_path)
        logger.debug("Downloaded DejaVu TTF zip to %s", zip_path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                logger.warning(
                    "Failed to remove temporary zip file: %s", tmp_path
                )


def _extract_needed_ttf(
    zip_path: str, needed: Dict[str, str], target: str
) -> bool:
    """Extract only needed TTF files from the archive into target.

    Returns True if all requested files are present after extraction.
    """

    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = {nm: nm for nm in zf.namelist()}

            # Map requested filenames to archive members (match by basename)
            to_extract: Dict[str, str] = {}
            for base in needed.values():
                match = None
                for nm in names:
                    if nm.lower().endswith(f"/{base.lower()}") or (
                        os.path.basename(nm).lower() == base.lower()
                    ):
                        match = nm
                        break
                if match:
                    to_extract[base] = match

            # Extract
            for base, member in to_extract.items():
                dest_path = os.path.join(target, base)
                if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
                    continue
                with zf.open(member) as src, open(dest_path, "wb") as dst:
                    dst.write(src.read())
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to extract fonts from zip: %s", exc)
        return False

    # Verify all files now exist
    for base in needed.values():
        if not os.path.exists(os.path.join(target, base)):
            return False
    return True


def _ensure_files(filenames: Dict[str, str]) -> Optional[FontPaths]:
    """Ensure required font files exist in the cache; download if missing."""

    target = _fonts_dir()
    resolved: Dict[str, str] = {}

    # First, check if present in env dir or cache dir
    missing: Dict[str, str] = {}
    for style, name in filenames.items():
        path = os.path.join(target, name)
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            missing[style] = name
        else:
            resolved[style] = path

    # If anything is missing, download the official TTF zip and extract
    if missing:
        zip_path = os.path.join(target, f"dejavu-ttf-{DEJAVU_VERSION}.zip")
        try:
            _ensure_zip_downloaded(zip_path)
            ok = _extract_needed_ttf(zip_path, filenames, target)
            if not ok:
                return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("Font zip handling failed: %s", exc)
            return None

        # Refresh resolved after extraction
        resolved = {
            style: os.path.join(target, name)
            for style, name in filenames.items()
        }

    return FontPaths(
        normal=resolved["normal"],
        bold=resolved["bold"],
        italic=resolved["italic"],
        boldItalic=resolved["boldItalic"],
    )


def _register_family(family: str, paths: FontPaths) -> None:
    """Register a TTF family and add bold/italic mappings."""

    from reportlab.lib.fonts import addMapping  # type: ignore
    from reportlab.pdfbase import pdfmetrics  # type: ignore
    from reportlab.pdfbase.ttfonts import TTFont  # type: ignore

    # Register each face only if needed
    mapping = {
        "": (paths.normal, family),
        "-Bold": (paths.bold, f"{family}-Bold"),
        "-Italic": (paths.italic, f"{family}-Italic"),
        "-BoldItalic": (paths.boldItalic, f"{family}-BoldItalic"),
    }

    for suffix, (ttf_path, name) in mapping.items():
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, ttf_path))

    addMapping(family, 0, 0, family)
    addMapping(family, 1, 0, f"{family}-Bold")
    addMapping(family, 0, 1, f"{family}-Italic")
    addMapping(family, 1, 1, f"{family}-BoldItalic")


def ensure_dejavu_fonts() -> str:
    """Ensure DejaVu Serif fonts are available and registered.

    Returns:
        The chosen family name: "DejaVuSerifCondensed", "DejaVuSerif",
        or a safe fallback "Helvetica" if registration fails.
    """

    # Try Condensed first
    try:
        paths = _ensure_files(DEJAVU_SERIF_CONDENSED)
        if paths:
            _register_family("DejaVuSerifCondensed", paths)
            return "DejaVuSerifCondensed"
    except Exception as exc:  # noqa: BLE001
        logger.info(
            "Condensed DejaVu registration failed, will try regular: %s", exc
        )

    # Fall back to regular DejaVu Serif
    try:
        paths = _ensure_files(DEJAVU_SERIF)
        if paths:
            _register_family("DejaVuSerif", paths)
            return "DejaVuSerif"
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Regular DejaVu registration failed, falling back to Helvetica: %s",
            exc,
        )

    # Last resort
    return "Helvetica"


__all__ = [
    "ensure_dejavu_fonts",
]
