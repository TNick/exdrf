"""Tests for list-relation route spec helpers (stdlib-only module)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

_LIST_ROUTE_PATH = (
    Path(__file__).resolve().parents[1]
    / "exdrf_gen_al2r"
    / "list_route_specs.py"
)


def _load_list_route_specs():
    """Load :mod:`exdrf_gen_al2r.list_route_specs` without importing the package."""

    spec = importlib.util.spec_from_file_location(
        "_exdrf_gen_al2r_list_route_specs_test",
        _LIST_ROUTE_PATH,
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_lrs = _load_list_route_specs()
parse_paged_list_inner_type = _lrs.parse_paged_list_inner_type
build_al2r_list_relation_route_specs = _lrs.build_al2r_list_relation_route_specs


def test_parse_paged_list_inner_type() -> None:
    """Inner name is extracted from a plain ``PagedList[T]`` annotation."""

    assert parse_paged_list_inner_type("PagedList[Tag]") == "Tag"
    assert parse_paged_list_inner_type("  PagedList[Post]  ") == "Post"
    assert parse_paged_list_inner_type("list[Tag]") is None
    assert parse_paged_list_inner_type("") is None


def test_build_al2r_list_relation_route_specs_skips_non_lists() -> None:
    """Only ``is_list_relation`` fields with parseable annotations are kept."""

    pd_kw = {
        "al2pd_ex_ref_fields": (
            SimpleNamespace(
                name="tags",
                annotation="PagedList[Tag]",
                is_list_relation=True,
            ),
            SimpleNamespace(
                name="owner",
                annotation="User | None",
                is_list_relation=False,
            ),
        ),
    }
    specs = build_al2r_list_relation_route_specs(pd_kw)
    assert specs == [{"attr": "tags", "related_name": "Tag"}]
