"""Tests for the comparator merge delegate (method/result editors)."""

from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QComboBox, QLineEdit, QWidget

from exdrf_qt.comparator.models.tree import (
    EDIT_ROLE,
    ComparatorTreeModel,
)
from exdrf_qt.comparator.widgets.merge_delegate import ComparatorMergeDelegate


def test_merge_delegate_create_editor_method_column(manager_factory, qt_app):
    """Delegate creates a combo box for the method column."""
    mgr = manager_factory()
    model = ComparatorTreeModel(manager=mgr, merge_enabled=True)
    delegate = ComparatorMergeDelegate(None)

    root = QModelIndex()
    row = 0
    while row < model.rowCount(root):
        idx = model.index(row, 0, root)
        node = idx.internalPointer()
        if getattr(node, "values", None) is not None:
            break
        row += 1
    assert row < model.rowCount(root)
    method_col = model._method_column()
    method_idx = model.index(row, method_col, root)

    parent = QWidget()
    editor = delegate.createEditor(parent, None, method_idx)
    assert editor is not None
    assert isinstance(editor, QComboBox)
    n = editor.count()
    assert n >= 4


def test_merge_delegate_create_editor_result_column_manual(
    manager_factory, qt_app
):
    """Delegate creates line edit for result when method is manual."""
    mgr = manager_factory()
    model = ComparatorTreeModel(manager=mgr, merge_enabled=True)
    delegate = ComparatorMergeDelegate(None)

    root = QModelIndex()
    row = 0
    while row < model.rowCount(root):
        idx = model.index(row, 0, root)
        node = idx.internalPointer()
        if getattr(node, "values", None) is not None:
            break
        row += 1
    assert row < model.rowCount(root)
    result_col = model._result_column()
    result_idx = model.index(row, result_col, root)

    model.setData(
        model.index(row, model._method_column(), root),
        "manual",
        EDIT_ROLE,
    )
    editor = delegate.createEditor(QWidget(), None, result_idx)
    assert editor is not None
    assert isinstance(editor, QLineEdit)
