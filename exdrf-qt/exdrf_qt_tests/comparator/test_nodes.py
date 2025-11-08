from exdrf_qt.comparator.logic.manager import ComparatorManager
from exdrf_qt.comparator.logic.nodes import (
    BaseNode,
    LeafNode,
    ParentNode,
    Value,
)


def test_base_parent_leaf_properties():
    mgr = ComparatorManager()
    base = BaseNode(manager=mgr, key="k", label="lbl")
    assert base.is_leaf is False
    assert base.is_parent is True
    assert base.is_root is True
    assert base.child_count == 0

    parent = ParentNode(manager=mgr, key="p", label="Parent")
    child_leaf = LeafNode(manager=mgr, key="c", label="Child", parent=parent)
    parent.add_child(child_leaf)
    assert parent.child_count == 1
    assert parent.compare(child_leaf, child_leaf) == -1


def test_leaf_equality_similarity_and_html_diff():
    mgr = ComparatorManager()
    parent = ParentNode(manager=mgr, key="p", label="P")

    # Equal values across two sources
    leaf_equal = LeafNode(manager=mgr, key="e", label="E", parent=parent)
    leaf_equal.values = [
        Value(True, "SAME", leaf_equal, source="A"),
        Value(True, "SAME", leaf_equal, source="B"),
    ]
    assert leaf_equal.are_equal is True

    # Exists/value mismatches are not equal
    leaf_miss = LeafNode(manager=mgr, key="m", label="M", parent=parent)
    leaf_miss.values = [
        Value(True, "X", leaf_miss, source="A"),
        Value(False, None, leaf_miss, source="B"),
    ]
    assert leaf_miss.are_equal is False

    # Similarity check (abc vs abx) should be True at default threshold
    tmp = LeafNode(manager=mgr, key="t", label="T", parent=parent)
    assert tmp.is_similar_enough("abc", "abx") is True

    # html_diff marks replaces with spans
    left_html, right_html = tmp.html_diff("foo", "f0o")
    assert 'class="del"' in left_html or 'class="ins"' in right_html
