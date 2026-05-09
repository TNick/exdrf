"""Tests for :class:`~exdrf_pd.sort_item.SortItem`."""

from __future__ import annotations

import json

import pytest
from pydantic import TypeAdapter, ValidationError

from exdrf_pd.sort_item import SortItem


def test_package_exports_sort_item() -> None:
    """``from exdrf_pd import SortItem`` re-exports the model."""

    from exdrf_pd import SortItem as SortItemFromRoot

    assert SortItemFromRoot is SortItem


class TestSortItem:
    """Validation and JSON round-trip for :class:`SortItem`."""

    def test_accepts_asc_desc(self) -> None:
        """Both literal orders validate."""

        assert SortItem(attr="id", order="asc").order == "asc"
        assert SortItem(attr="id", order="desc").order == "desc"

    def test_rejects_invalid_order(self) -> None:
        """Unknown direction raises validation error."""

        with pytest.raises(ValidationError):
            SortItem(attr="x", order="up")  # type: ignore[arg-type]

    def test_json_roundtrip_list(self) -> None:
        """``TypeAdapter`` parses the JSON list shape used in query strings."""

        raw = json.dumps(
            [
                {"attr": "name", "order": "asc"},
                {"attr": "id", "order": "desc"},
            ],
        )
        adapter = TypeAdapter(list[SortItem])
        items = adapter.validate_json(raw.encode("utf-8"))
        assert len(items) == 2
        assert items[0].attr == "name"
        assert items[1].order == "desc"
