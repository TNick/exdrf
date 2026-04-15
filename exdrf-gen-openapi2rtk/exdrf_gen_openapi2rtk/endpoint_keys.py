"""RTK ``injectEndpoints`` key uniqueness for OpenAPI-derived routes."""

from __future__ import annotations

from typing import Any


def assert_unique_rtk_endpoint_keys(category: str, routes: list[Any]) -> None:
    """Fail fast when two routes would share the same RTK endpoint object key.

    Args:
        category: OpenAPI primary tag / grouping label for the emitted file.
        routes: Route objects with ``name_camel`` (camelCase operation key).

    Raises:
        ValueError: When two routes share the same ``name_camel``.
    """

    seen: dict[str, str] = {}
    for route in routes:
        key = route.name_camel
        if key in seen:
            raise ValueError(
                "Duplicate RTK endpoint key %r in category %r: paths %r vs %r. "
                "Adjust ``operationId`` values or OpenAPI tags so keys are "
                "unique within each emitted module."
                % (key, category, seen[key], getattr(route, "path", "?"))
            )
        seen[key] = getattr(route, "path", "?")
