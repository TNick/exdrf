"""Tests for ``exdrf_pd.paged`` and ``exdrf_pd.schema_extra`` primitives."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from exdrf_pd.paged import PagedList, paged_list_empty_factory
from exdrf_pd.schema_extra import (
    EXDRF_JSON_SCHEMA_EXTRA_KEY,
    wrap_exdrf_props,
)


class TestPagedList:
    """Covers validation, defaults, and ``extra="forbid"`` for paging models."""

    def test_round_trip_simple_items(self) -> None:
        """A populated page validates and preserves counters."""

        page = PagedList[int](
            total=100,
            offset=10,
            page_size=20,
            items=[1, 2],
        )
        assert page.total == 100
        assert page.offset == 10
        assert page.page_size == 20
        assert page.items == [1, 2]

    def test_empty_classmethod(self) -> None:
        """``empty()`` yields a zeroed envelope with no items."""

        page = PagedList[int].empty()
        assert page.total == 0
        assert page.offset == 0
        assert page.page_size == 0
        assert page.items == []

    def test_paged_list_empty_factory_matches_empty(self) -> None:
        """The forward-ref-safe factory matches ``PagedList[Any].empty()``."""

        from_any = paged_list_empty_factory()
        typed_empty = PagedList[int].empty()
        assert from_any.model_dump() == typed_empty.model_dump()

    def test_rejects_extra_keys(self) -> None:
        """Unknown fields are rejected."""

        with pytest.raises(ValidationError):
            PagedList[int].model_validate(
                {
                    "total": 0,
                    "offset": 0,
                    "page_size": 0,
                    "items": [],
                    "unexpected": True,
                }
            )

    def test_json_schema_includes_core_properties(self) -> None:
        """OpenAPI-oriented schema lists the stable paging field names."""

        class Item(BaseModel):
            """Minimal nested item."""

            id: int

        schema = PagedList[Item].model_json_schema()
        props = set(schema.get("properties", {}))
        assert props == {"total", "offset", "page_size", "items"}


class TestWrapExdrfProps:
    """Tests for :func:`wrap_exdrf_props`."""

    def test_nests_under_exdrf_key(self) -> None:
        """Props are wrapped under :data:`EXDRF_JSON_SCHEMA_EXTRA_KEY`."""

        wrapped = wrap_exdrf_props({"kind": "list", "resource": "towns"})
        assert set(wrapped.keys()) == {EXDRF_JSON_SCHEMA_EXTRA_KEY}
        assert wrapped[EXDRF_JSON_SCHEMA_EXTRA_KEY] == {
            "kind": "list",
            "resource": "towns",
        }
