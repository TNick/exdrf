"""Constants for embedding exdrf metadata in Pydantic JSON schema extras."""

from __future__ import annotations

from typing import Any, Mapping

# Key used under ``Field(json_schema_extra=...)`` / ``model_config`` so
# OpenAPI and clients can find exdrf field/resource metadata without
# colliding with other extensions.
EXDRF_JSON_SCHEMA_EXTRA_KEY = "exdrf"


def wrap_exdrf_props(props: Mapping[str, Any]) -> dict[str, Any]:
    """Nest exdrf properties under :data:`EXDRF_JSON_SCHEMA_EXTRA_KEY`.

    Args:
        props: Field or resource properties (JSON-serializable values).

    Returns:
        A single-key dict suitable for ``json_schema_extra``.
    """
    return {EXDRF_JSON_SCHEMA_EXTRA_KEY: dict(props)}
