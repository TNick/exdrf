"""Tests for shortening FastAPI-style ``operationId`` values."""

from __future__ import annotations

from exdrf_gen_openapi2rtk.spec_routes import routes_by_primary_tag


def test_strips_generated_path_suffix_from_operation_id() -> None:
    """``*_generated_*_<verb>`` tails collapse to the handler prefix."""

    spec = {
        "openapi": "3.1.0",
        "info": {"title": "T", "version": "1"},
        "paths": {
            "/generated/foo/items": {
                "get": {
                    "tags": ["items"],
                    "operationId": ("list_item_generated_foo_items_get"),
                    "responses": {"200": {"description": "ok"}},
                }
            }
        },
        "components": {"schemas": {}},
    }
    by_tag = routes_by_primary_tag(spec)
    assert by_tag["items"][0].name_snake_case == "list_item"
    assert by_tag["items"][0].name_camel == "listItem"
