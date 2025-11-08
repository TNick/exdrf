from PyQt5.QtCore import QItemSelectionModel, QModelIndex
from PyQt5.QtWidgets import QApplication

from exdrf_qt.comparator.widgets.tree import ComparatorTreeView


def _find_row_by_label(
    view: ComparatorTreeView, parent: QModelIndex, label: str
) -> int:
    model = view.model()
    rows = model.rowCount(parent)
    for r in range(rows):
        idx = model.index(r, 0, parent)
        if model.data(idx) == label:
            return r
    return -1


def test_expand_and_copy_yaml(manager_factory, qt_app: QApplication):
    mgr = manager_factory()
    view = ComparatorTreeView(manager=mgr)

    # Expand only branches with differences
    view.expand_diff_branches()
    model = view.model()
    root = QModelIndex()

    # "Group" has a nested_missing difference -> its index should be expanded
    grp_row = _find_row_by_label(view, root, "Group")
    assert grp_row >= 0
    grp_idx = model.index(grp_row, 0, root)
    assert view.isExpanded(grp_idx) is True

    # Copy ALL
    view.copy_all_as_yaml()
    text_all = QApplication.clipboard().text()
    assert "type: parent" in text_all
    assert "label: Group" in text_all
    assert "label: Nested Missing" in text_all

    # Select only "Group" and copy selection
    sel = view.selectionModel()
    sel.select(
        grp_idx,
        QItemSelectionModel.Select
        | QItemSelectionModel.Rows
        | QItemSelectionModel.Current,
    )
    view.copy_selection_as_yaml()
    text_sel = QApplication.clipboard().text()
    assert "label: Group" in text_sel
    # Root-only fields should not appear in the group-only export
    assert "label: Partial Field" not in text_sel
