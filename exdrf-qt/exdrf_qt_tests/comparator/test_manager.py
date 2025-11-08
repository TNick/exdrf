from typing import Optional

from exdrf_qt.comparator.logic.manager import ComparatorManager
from exdrf_qt.comparator.logic.nodes import LeafNode, ParentNode


def _find_child_by_key(
    parent: ParentNode, key: str
) -> Optional[LeafNode | ParentNode]:
    for ch in parent.children:
        if ch.key == key:
            return ch
    return None


def test_compare_merges_children_and_values(manager_factory):
    mgr: ComparatorManager = manager_factory()
    assert isinstance(mgr.root, ParentNode)

    # Direct children leaves
    k_equal = _find_child_by_key(mgr.root, "k_equal")
    assert isinstance(k_equal, LeafNode)
    assert len(k_equal.values) == 3
    assert all(v.exists for v in k_equal.values)
    assert len({v.value for v in k_equal.values}) == 1

    k_partial = _find_child_by_key(mgr.root, "k_partial")
    assert isinstance(k_partial, LeafNode)
    vals = [v.value for v in k_partial.values]
    assert vals[0] == vals[2] and vals[0] != vals[1]

    k_diff = _find_child_by_key(mgr.root, "k_diff")
    assert isinstance(k_diff, LeafNode)
    assert len({v.value for v in k_diff.values}) == 3

    only_first = _find_child_by_key(mgr.root, "only_first")
    assert isinstance(only_first, LeafNode)
    assert [v.exists for v in only_first.values] == [True, False, False]

    # Nested group checks
    grp = _find_child_by_key(mgr.root, "grp")
    assert isinstance(grp, ParentNode)
    nested_equal = _find_child_by_key(grp, "nested_equal")
    assert isinstance(nested_equal, LeafNode)
    assert len({v.value for v in nested_equal.values}) == 1

    nested_missing = _find_child_by_key(grp, "nested_missing")
    assert isinstance(nested_missing, LeafNode)
    assert [v.exists for v in nested_missing.values] == [False, True, False]
