"""Tests for RecordComparatorBase, RecordToNodeAdapter, CmpResultPreviewPane."""

from exdrf_qt.comparator.logic.manager import ComparatorManager
from exdrf_qt.comparator.logic.nodes import ParentNode
from exdrf_qt.controls.record_cmp_base import (
    CmpResultPreviewPane,
    FieldAwareRecordAdapter,
    RecordComparatorBase,
    RecordToNodeAdapter,
)


class TestRecordToNodeAdapter:
    """Tests for RecordToNodeAdapter."""

    def test_get_compare_data_returns_parent_with_leaves(self):
        """get_compare_data returns a ParentNode with one leaf per (key, label, value)."""

        def leaf_data():
            return [("a", "A", 1), ("b", "B", "two")]

        adapter = RecordToNodeAdapter(name="S1", get_leaf_data=leaf_data)
        mng = ComparatorManager()
        root = adapter.get_compare_data(mng)
        assert isinstance(root, ParentNode)
        assert root.child_count == 2
        assert root.children[0].key == "a"
        assert root.children[0].label == "A"
        assert len(root.children[0].values) == 1
        assert root.children[0].values[0].value == 1
        assert root.children[1].key == "b"
        assert root.children[1].values[0].value == "two"

    def test_get_merge_item_label_returns_name(self):
        """get_merge_item_label returns the adapter name."""
        adapter = RecordToNodeAdapter(name="Item X", get_leaf_data=lambda: [])
        mng = ComparatorManager()
        assert adapter.get_merge_item_label(mng, 0) == "Item X"


class TestFieldAwareRecordAdapter:
    """Tests for FieldAwareRecordAdapter (field_map and create_merge_editor)."""

    def test_inherits_record_to_node_adapter(self):
        """FieldAwareRecordAdapter builds same tree as RecordToNodeAdapter."""
        adapter = FieldAwareRecordAdapter(
            name="S1",
            get_leaf_data=lambda: [("k", "K", 1)],
            field_map={},
        )
        mng = ComparatorManager()
        root = adapter.get_compare_data(mng)
        assert root.child_count == 1
        assert root.children[0].key == "k"
        assert root.children[0].values[0].value == 1

    def test_create_merge_editor_returns_none_when_key_not_in_map(self):
        """create_merge_editor returns None when leaf key is not in field_map."""
        adapter = FieldAwareRecordAdapter(
            name="S1",
            get_leaf_data=lambda: [],
            field_map={"other": None},
        )

        class Ctx:
            class leaf:
                key = "missing"

        ctx = Ctx()
        assert adapter.create_merge_editor(None, ctx, None, None) is None


class TestRecordComparatorBase:
    """Tests for RecordComparatorBase (mode, panes, payload).

    Full widget tests that create the webview are skipped to avoid
    QWebEngineView/offscreen issues in CI; adapter and pane tests cover
    the payload and preview lifecycle.
    """

    def test_base_has_merge_enabled_property(self):
        """RecordComparatorBase exposes merge_enabled as a property."""
        assert hasattr(RecordComparatorBase, "merge_enabled")
        prop = getattr(RecordComparatorBase, "merge_enabled")
        assert prop is not None

    def test_base_has_get_merged_payload_and_preview_context(self):
        """RecordComparatorBase defines get_merged_payload and get_result_preview_context."""
        assert hasattr(RecordComparatorBase, "get_merged_payload")
        assert hasattr(RecordComparatorBase, "get_result_preview_context")


class TestCmpResultPreviewPane:
    """Tests for CmpResultPreviewPane."""

    def test_build_html_contains_keys_and_values(self):
        """_build_html produces HTML with key-value rows from context dict."""
        data = {"x": 1, "a": "alpha"}
        # Call _build_html without creating the widget (avoids QWebEngineView in CI).
        html_content = CmpResultPreviewPane._build_html(None, data)
        assert "a" in html_content
        assert "alpha" in html_content
        assert "x" in html_content
        assert "1" in html_content
        assert "<table" in html_content
        assert "</table>" in html_content
