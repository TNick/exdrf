"""Tests for comparator merge logic: method resolution and strategy/adapter."""

from exdrf_qt.comparator.logic.merge import (
    MERGE_METHOD_FIRST_NOT_NULL,
    MERGE_METHOD_MANUAL,
    MERGE_METHOD_SET_NULL,
    DefaultMergeStrategy,
    LeafMergeState,
    MergeContext,
    merge_method_item,
    parse_item_method_id,
)
from exdrf_qt.comparator.logic.nodes import LeafNode


def _find_leaf_by_key(parent, key: str):
    """Return first descendant leaf with given key."""
    for ch in parent.children:
        if isinstance(ch, LeafNode) and ch.key == key:
            return ch
        if hasattr(ch, "children"):
            found = _find_leaf_by_key(ch, key)
            if found is not None:
                return found
    return None


class TestMergeMethodIds:
    """Tests for merge method ID helpers."""

    def test_merge_method_item(self):
        assert merge_method_item(0) == "item:0"
        assert merge_method_item(1) == "item:1"

    def test_parse_item_method_id(self):
        assert parse_item_method_id("item:0") == 0
        assert parse_item_method_id("item:1") == 1
        assert parse_item_method_id("first_not_null") is None
        assert parse_item_method_id("item:") is None


class TestDefaultMergeStrategy:
    """Tests for DefaultMergeStrategy resolution and options."""

    def test_get_item_labels_default(self, manager_factory):
        mgr = manager_factory()
        leaf = _find_leaf_by_key(mgr.root, "k_equal")
        assert leaf is not None
        ctx = MergeContext(leaf=leaf, manager=mgr, values=leaf.values)
        strategy = DefaultMergeStrategy()
        labels = strategy.get_item_labels(ctx, len(mgr.sources))
        assert labels == ["Item 1", "Item 2", "Item 3"]

    def test_get_item_labels_from_context(self, manager_factory):
        mgr = manager_factory()
        leaf = _find_leaf_by_key(mgr.root, "k_equal")
        assert leaf is not None
        ctx = MergeContext(
            leaf=leaf,
            manager=mgr,
            values=leaf.values,
            source_labels=["Source A", "Source B", "Source C"],
        )
        strategy = DefaultMergeStrategy()
        labels = strategy.get_item_labels(ctx, 3)
        assert labels == ["Source A", "Source B", "Source C"]

    def test_get_available_methods(self, manager_factory):
        mgr = manager_factory()
        leaf = _find_leaf_by_key(mgr.root, "k_equal")
        assert leaf is not None
        ctx = mgr.get_merge_context(leaf)
        strategy = DefaultMergeStrategy()
        opts = strategy.get_available_methods(ctx)
        ids = [o.id for o in opts]
        assert "item:0" in ids
        assert MERGE_METHOD_FIRST_NOT_NULL in ids
        assert MERGE_METHOD_SET_NULL in ids
        assert MERGE_METHOD_MANUAL in ids

    def test_resolve_value_item(self, manager_factory):
        mgr = manager_factory()
        leaf = _find_leaf_by_key(mgr.root, "k_diff")
        assert leaf is not None
        ctx = MergeContext(leaf=leaf, manager=mgr, values=leaf.values)
        strategy = DefaultMergeStrategy()
        state = LeafMergeState(selected_method="item:0")
        assert strategy.resolve_value(ctx, state) == "D-A"
        state = LeafMergeState(selected_method="item:1")
        assert strategy.resolve_value(ctx, state) == "D-B"

    def test_resolve_value_first_not_null(self, manager_factory):
        mgr = manager_factory()
        leaf = _find_leaf_by_key(mgr.root, "only_first")
        assert leaf is not None
        state = LeafMergeState(selected_method=MERGE_METHOD_FIRST_NOT_NULL)
        leaf.merge_state = state
        assert mgr.resolve_merge_value(leaf) == "ONLY-A"

    def test_resolve_value_set_null(self, manager_factory):
        mgr = manager_factory()
        leaf = _find_leaf_by_key(mgr.root, "k_equal")
        assert leaf is not None
        state = LeafMergeState(selected_method=MERGE_METHOD_SET_NULL)
        leaf.merge_state = state
        assert mgr.resolve_merge_value(leaf) is None

    def test_resolve_value_manual(self, manager_factory):
        mgr = manager_factory()
        leaf = _find_leaf_by_key(mgr.root, "k_equal")
        assert leaf is not None
        state = LeafMergeState(
            selected_method=MERGE_METHOD_MANUAL,
            manual_value="custom",
        )
        leaf.merge_state = state
        assert mgr.resolve_merge_value(leaf) == "custom"


class TestManagerMergeHelpers:
    """Tests for manager get_available_merge_methods and get_merged_payload."""

    def test_get_available_merge_methods_uses_strategy(self, manager_factory):
        mgr = manager_factory()
        leaf = _find_leaf_by_key(mgr.root, "k_equal")
        assert leaf is not None
        opts = mgr.get_available_merge_methods(leaf)
        assert len(opts) >= 4
        assert any(o.id == "item:0" for o in opts)

    def test_get_merged_payload(self, manager_factory):
        mgr = manager_factory()
        payload = mgr.get_merged_payload()
        assert "k_equal" in payload
        assert payload["k_equal"] == "SAME"
        assert "grp.nested_equal" in payload
        assert payload["grp.nested_equal"] == 42
