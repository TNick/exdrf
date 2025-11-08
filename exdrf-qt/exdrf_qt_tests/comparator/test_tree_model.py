from typing import Optional, Tuple

from PyQt5.QtCore import QModelIndex
from PyQt5.QtGui import QBrush, QColor

from exdrf_qt.comparator.models.tree import (
    BACKGROUND_ROLE,
    DISPLAY_ROLE,
    HORIZONTAL,
    HTML_ROLE,
    ComparatorTreeModel,
)


def _find_row_by_label(
    model: ComparatorTreeModel, parent: QModelIndex, label: str
) -> int:
    rows = model.rowCount(parent)
    for r in range(rows):
        idx = model.index(r, 0, parent)
        if model.data(idx, DISPLAY_ROLE) == label:
            return r
    return -1


def _child_index_by_label(
    model: ComparatorTreeModel, parent: QModelIndex, label: str
) -> Optional[QModelIndex]:
    r = _find_row_by_label(model, parent, label)
    if r < 0:
        return None
    return model.index(r, 0, parent)


def test_tree_model_columns_headers_and_roles(manager_factory, qt_app):
    mgr = manager_factory()
    model = ComparatorTreeModel(manager=mgr)

    # Columns: 1 label + N sources
    assert model.columnCount() == 1 + len(mgr.sources) == 4

    # Headers
    assert model.headerData(0, HORIZONTAL, DISPLAY_ROLE) == "Field"
    assert model.headerData(1, HORIZONTAL, DISPLAY_ROLE) == "Source A"
    assert model.headerData(2, HORIZONTAL, DISPLAY_ROLE) == "Source B"
    assert model.headerData(3, HORIZONTAL, DISPLAY_ROLE) == "Source C"

    root_index = QModelIndex()

    # Locate rows
    idx_equal = _child_index_by_label(model, root_index, "Equal Field")
    idx_partial = _child_index_by_label(model, root_index, "Partial Field")
    idx_diff = _child_index_by_label(model, root_index, "Diff Field")
    idx_grp = _child_index_by_label(model, root_index, "Group")
    assert idx_equal and idx_partial and idx_diff and idx_grp

    # Background colors (leafs only)
    def _color_for(idx) -> Tuple[int, int, int]:
        br = model.data(idx, BACKGROUND_ROLE)
        assert isinstance(br, QBrush)
        c: QColor = br.color()
        return (c.red(), c.green(), c.blue())

    # equal -> light green
    assert _color_for(idx_equal) == (220, 255, 220)
    # partial -> light orange
    assert _color_for(idx_partial) == (255, 240, 220)
    # mismatch example: a leaf present only in first source -> light red
    idx_only_first = _child_index_by_label(model, root_index, "Only First")
    assert idx_only_first is not None
    assert _color_for(idx_only_first) == (255, 220, 220)

    # HTML diffs: left side in column 0 for partial
    left_html = model.data(idx_partial, HTML_ROLE)
    assert isinstance(left_html, str) and "<span" in left_html

    # Right-side diff in the B column (section 2 -> src_idx 1)
    idx_partial_b = model.index(idx_partial.row(), 2, root_index)
    right_html = model.data(idx_partial_b, HTML_ROLE)
    assert isinstance(right_html, str) and "<span" in right_html
