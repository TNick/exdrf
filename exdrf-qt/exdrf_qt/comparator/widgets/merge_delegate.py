"""Delegate for merge Method and Result columns in the comparator tree.

Provides a combo box for the method column and a line edit (or custom editor
from adapter/strategy) for the result column when method is manual. Result
is read-only for non-manual methods.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from PyQt5.QtCore import QModelIndex, Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QLineEdit,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QWidget,
)

from exdrf_qt.comparator.logic.merge import MERGE_METHOD_MANUAL
from exdrf_qt.comparator.models.tree import (
    MERGE_CONTEXT_ROLE,
    MERGE_METHOD_ROLE,
    MERGE_OPTIONS_ROLE,
    MERGE_RESULT_ROLE,
    MERGE_STATE_ROLE,
)

logger = logging.getLogger(__name__)


class ComparatorMergeDelegate(QStyledItemDelegate):
    """Delegate for editing merge Method and Result columns.

    Method column: combo box of available methods. Result column: for manual
    method, line edit or custom editor from adapter; otherwise read-only.
    """

    def createEditor(
        self,
        parent: QWidget,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> Optional[QWidget]:
        model = index.model()
        if model is None:
            return None
        col = index.column()

        # Method column: always combo of options.
        if col == self._method_column(model):
            opts = model.data(index, MERGE_OPTIONS_ROLE)
            if not opts:
                return None
            combo = QComboBox(parent)
            for opt in opts:
                combo.addItem(opt.label, opt.id)
            return combo

        # Result column: only when method is manual; try custom editor first.
        if col == self._result_column(model):
            state = model.data(index, MERGE_STATE_ROLE)
            if state is None or state.selected_method != MERGE_METHOD_MANUAL:
                return None
            context = model.data(index, MERGE_CONTEXT_ROLE)
            current = model.data(index, MERGE_RESULT_ROLE)
            if context is not None and context.manager is not None:
                for adapter in context.manager.sources:
                    editor = adapter.create_merge_editor(
                        parent, context, state, current
                    )
                    if editor is not None:
                        return editor
            return QLineEdit(parent)

        return None

    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        model = index.model()
        if model is None:
            return
        col = index.column()

        if col == self._method_column(model):
            if isinstance(editor, QComboBox):
                method_id = model.data(index, MERGE_METHOD_ROLE)
                for i in range(editor.count()):
                    if editor.itemData(i) == method_id:
                        editor.setCurrentIndex(i)
                        return
            return

        if col == self._result_column(model):
            val = model.data(index, MERGE_RESULT_ROLE)
            text = "" if val is None else str(val)
            if isinstance(editor, QLineEdit):
                editor.setText(text)

    def setModelData(
        self,
        editor: QWidget,
        model: Any,
        index: QModelIndex,
    ) -> None:
        if model is None:
            return
        col = index.column()

        if col == self._method_column(model):
            if isinstance(editor, QComboBox):
                method_id = editor.currentData()
                if method_id is not None:
                    model.setData(index, method_id, Qt.EditRole)
            return

        if col == self._result_column(model):
            if isinstance(editor, QLineEdit):
                model.setData(index, editor.text(), Qt.EditRole)

    def updateEditorGeometry(
        self,
        editor: QWidget,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        editor.setGeometry(option.rect)

    def _method_column(self, model: Any) -> int:
        """Method column index from model."""
        num = getattr(model, "num_sources", 0)
        return 1 + num

    def _result_column(self, model: Any) -> int:
        """Result column index from model."""
        num = getattr(model, "num_sources", 0)
        return 2 + num
