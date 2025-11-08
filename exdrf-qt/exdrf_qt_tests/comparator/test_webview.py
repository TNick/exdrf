import importlib
import sys
from types import ModuleType
from typing import Any, Dict, List

import pytest


class _DummyTemplViewer:
    def __init__(self, *args, **kwargs) -> None:
        self.init_kwargs = kwargs
        self.render_calls: List[Dict[str, Any]] = []

    def render_template(self, **ctx) -> None:
        self.render_calls.append(ctx)


@pytest.fixture
def webview_module(monkeypatch):
    # Inject a dummy TemplViewer to avoid QtWebEngine dependencies.
    fake_mod = ModuleType("exdrf_qt.controls.templ_viewer.templ_viewer")
    fake_mod.TemplViewer = _DummyTemplViewer  # type: ignore[attr-defined]
    sys.modules["exdrf_qt.controls.templ_viewer.templ_viewer"] = fake_mod
    # Force reload of webview with the monkeypatched TemplViewer
    mod = importlib.import_module("exdrf_qt.comparator.widgets.webview")
    importlib.reload(mod)
    yield mod


def _find_leaf_by_key(root_dict, key: str):
    for ch in root_dict["children"]:
        if ch.get("type") == "leaf" and ch.get("key") == key:
            return ch
        if ch.get("type") == "parent":
            nested = _find_leaf_by_key(
                {"children": ch.get("children", [])}, key
            )
            if nested:
                return nested
    return None


def test_webview_context_and_refresh(manager_factory, webview_module, context):
    ComparatorWebView = getattr(webview_module, "ComparatorWebView")
    mgr = manager_factory()
    vw = ComparatorWebView(ctx=context, manager=mgr, parent=None)

    # Verify source names and tree
    ctx_dict = vw._build_context()
    assert ctx_dict["source_names"] == ["Source A", "Source B", "Source C"]
    assert ctx_dict["num_sources"] == 3
    tree = ctx_dict["tree"]
    assert isinstance(tree, dict) and "children" in tree

    # Extract cells for a partial leaf; ensure HTML diffs exist
    # Walk the manager tree to find a leaf node object for "k_partial"
    from exdrf_qt.comparator.logic.nodes import LeafNode, ParentNode

    def find_leaf(node, key):
        for ch in node.children:
            if isinstance(ch, LeafNode) and ch.key == key:
                return ch
            if isinstance(ch, ParentNode):
                got = find_leaf(ch, key)
                if got:
                    return got
        return None

    leaf = find_leaf(mgr.root, "k_partial")
    cells = vw._extract_leaf_values(leaf)
    assert len(cells) == 3
    # There should be inline diffs for at least the base and B values
    assert isinstance(cells[0]["html"], str)
    assert isinstance(cells[1]["html"], str)
    assert "<span" in cells[1]["html"] or "<span" in cells[0]["html"]

    # Status helpers
    leaf_equal = find_leaf(mgr.root, "k_equal")
    assert vw._get_leaf_status(leaf_equal) == "same"
    leaf_only_first = find_leaf(mgr.root, "only_first")
    assert vw._get_leaf_status(leaf_only_first) == "left_only"
    leaf_nested_missing = find_leaf(mgr.root, "nested_missing")
    assert vw._get_leaf_status(leaf_nested_missing) == "right_only"
    leaf_diff = find_leaf(mgr.root, "k_diff")
    assert vw._get_leaf_status(leaf_diff) == "modified"

    # Refresh should call render_template with updated context
    before = len(vw.render_calls) if hasattr(vw, "render_calls") else 0
    vw.refresh()
    after = len(vw.render_calls) if hasattr(vw, "render_calls") else 0
    assert after >= before + 1
