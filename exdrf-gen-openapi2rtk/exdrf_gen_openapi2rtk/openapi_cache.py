"""Load OpenAPI JSON from disk or URL with optional cache metadata."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Mapping

logger = logging.getLogger(__name__)


def _validate_openapi_root(doc: Mapping[str, Any]) -> None:
    """Ensure ``doc`` looks like an OpenAPI 3.x document.

    Args:
        doc: Parsed JSON root.

    Raises:
        ValueError: When required top-level keys are missing.
    """

    if "openapi" not in doc and "swagger" not in doc:
        raise ValueError("OpenAPI document must contain an 'openapi' key.")
    if "paths" not in doc:
        raise ValueError("OpenAPI document must contain a 'paths' object.")


def load_openapi_from_file(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Read and validate OpenAPI JSON from a local file.

    Args:
        path: Filesystem path to ``openapi.json``.

    Returns:
        Parsed OpenAPI document as a ``dict``.
    """

    p = Path(path)
    text = p.read_text(encoding="utf-8")
    doc = json.loads(text)
    if not isinstance(doc, dict):
        raise ValueError("OpenAPI file must contain a JSON object at the root.")
    _validate_openapi_root(doc)
    return doc


def _meta_path(cache_file: Path) -> Path:
    """Sidecar path for cached HTTP metadata."""

    return cache_file.with_suffix(cache_file.suffix + ".meta.json")


def fetch_openapi_url_cached(
    url: str,
    cache_file: Path,
    *,
    timeout_s: float = 60.0,
) -> dict[str, Any]:
    """GET ``url``, write ``cache_file``, reuse body when ETag matches.

    Stores ``ETag`` / ``Last-Modified`` from the last successful response in a
    small JSON sidecar next to ``cache_file`` and sends ``If-None-Match`` on
    subsequent calls. If the server replies ``304``, the cached file body is
    re-read.

    Args:
        url: HTTP or HTTPS URL to ``openapi.json``.
        cache_file: Path where the latest document JSON is stored.
        timeout_s: Socket timeout for the HTTP request.

    Returns:
        Parsed OpenAPI document.
    """

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    meta_fp = _meta_path(cache_file)
    etag: str | None = None
    if meta_fp.is_file():
        try:
            meta = json.loads(meta_fp.read_text(encoding="utf-8"))
            etag = meta.get("etag")
        except OSError as exc:
            logger.log(
                1,
                "Could not read OpenAPI cache meta %s: %s",
                meta_fp,
                exc,
                exc_info=True,
            )
    req = urllib.request.Request(url)
    if etag:
        req.add_header("If-None-Match", etag)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            status = getattr(resp, "status", 200)
            new_etag = resp.headers.get("ETag")
            new_lm = resp.headers.get("Last-Modified")
            if status == 304 and cache_file.is_file():
                body = cache_file.read_text(encoding="utf-8")
            else:
                body_bytes = resp.read()
                body = body_bytes.decode("utf-8")
                cache_file.write_text(body, encoding="utf-8")
            if new_etag or new_lm:
                meta_fp.write_text(
                    json.dumps({"etag": new_etag, "last_modified": new_lm}),
                    encoding="utf-8",
                )
    except urllib.error.HTTPError as exc:
        if exc.code == 304 and cache_file.is_file():
            body = cache_file.read_text(encoding="utf-8")
        else:
            logger.error(
                "OpenAPI HTTP fetch failed for %s with status %s",
                url,
                getattr(exc, "code", "?"),
                exc_info=True,
            )
            raise
    except urllib.error.URLError as exc:
        logger.error(
            "OpenAPI URL fetch failed for %s: %s",
            url,
            exc,
            exc_info=True,
        )
        raise
    doc = json.loads(body)
    if not isinstance(doc, dict):
        raise ValueError("OpenAPI URL must return a JSON object at the root.")
    _validate_openapi_root(doc)
    return doc


def snapshot_openapi_to_cache(doc: Mapping[str, Any], cache_file: Path) -> None:
    """Write a pretty-printed OpenAPI document to ``cache_file``.

    Args:
        doc: OpenAPI mapping to serialize.
        cache_file: Destination path (parent directories are created).
    """

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(
        json.dumps(doc, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
