"""Tests for ``list_query_specs`` (load module without package ``__init__``)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

_LIST_QUERY_PATH = (
    Path(__file__).resolve().parents[1]
    / "exdrf_gen_al2r"
    / "list_query_specs.py"
)


def _load_list_query_specs():
    """Load :mod:`exdrf_gen_al2r.list_query_specs` without importing the package."""

    spec = importlib.util.spec_from_file_location(
        "_exdrf_gen_al2r_list_query_specs_test",
        _LIST_QUERY_PATH,
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_lqs = _load_list_query_specs()
build_al2r_list_relation_query_specs = _lqs.build_al2r_list_relation_query_specs


def test_build_al2r_list_relation_query_specs_joins_sync() -> None:
    """Each list route spec gets the matching sync dict by ``ex_field_name``."""

    list_specs = [{"attr": "widgets", "related_name": "Widget"}]
    rel_specs = [
        {
            "ex_field_name": "widgets",
            "kind": "o2m_fk",
            "child_fk_col": "parent_id",
        }
    ]
    resource = SimpleNamespace(
        fields=(
            SimpleNamespace(
                name="widgets",
                is_list=True,
                ref=SimpleNamespace(primary_fields=lambda: ("id",)),
            ),
        )
    )
    merged = build_al2r_list_relation_query_specs(
        resource, list_specs, rel_specs
    )
    assert len(merged) == 1
    assert merged[0]["attr"] == "widgets"
    assert merged[0]["sync"]["kind"] == "o2m_fk"
    assert merged[0]["related_pk_col"] == "id"
