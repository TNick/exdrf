from __future__ import annotations

import logging
import sys
from typing import Optional

from PyQt5.QtWidgets import QApplication, QTreeView, QWidget, QVBoxLayout

from exdrf_qt.comparator.logic.adapter import ComparatorAdapter
from exdrf_qt.comparator.logic.manager import ComparatorManager
from exdrf_qt.comparator.logic.nodes import LeafNode, ParentNode, Value
from exdrf_qt.comparator.models.tree import ComparatorTreeModel

logger = logging.getLogger(__name__)


class ComparatorTreeView(QTreeView):
    """A tree view bound to a `ComparatorTreeModel`."""

    def __init__(
        self, manager: ComparatorManager, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._manager = manager
        self._model = ComparatorTreeModel(manager=self._manager, parent=self)
        self.setModel(self._model)

        # Cosmetic defaults.
        self.setUniformRowHeights(True)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(False)
        header = self.header()
        if header is not None:
            header.setStretchLastSection(True)
        for c in range(self._model.columnCount()):
            self.resizeColumnToContents(c)

    def refresh(self) -> None:
        """Rebuild the model from the current manager data."""
        self._model.beginResetModel()
        try:
            # Re-run compare to rebuild unified root.
            if not self._manager.data:
                self._manager.get_compare_data()
            self._manager.compare()
            self._model.num_sources = len(self._manager.sources)
            self._model.root = self._manager.root
        finally:
            self._model.endResetModel()
        for c in range(self._model.columnCount()):
            self.resizeColumnToContents(c)


# Demo with mock data sources
# --------------------------------------------------------------------------- #
class _MockAdapter(ComparatorAdapter):
    """Simple in-memory adapter for demo purposes."""

    def __init__(self, name: str, values_suffix: str) -> None:
        self.name = name
        self._suffix = values_suffix

    def get_compare_data(self, mng: "ComparatorManager") -> "ParentNode":
        # Helper factories
        def p(key: str, label: str, parent: ParentNode) -> ParentNode:
            node = ParentNode(manager=mng, key=key, label=label, parent=parent)
            parent.add_child(node)
            return node

        def leaf(key: str, label: str, value: str, parent: ParentNode) -> None:
            lf = LeafNode(manager=mng, key=key, label=label, parent=parent)
            # Add single value for this source; aligned in compare.
            lf.values = [
                Value(
                    exists=True,
                    value=value,
                    node=lf,
                    source=self,
                )
            ]
            parent.add_child(lf)

        # Root container for this source
        root = ParentNode(manager=mng, key="root", label=f"Root {self.name}")

        # Category A -> SubA1/SubA2 -> leaves (total 6)
        cat_a = p("cat_a", "Category A", root)
        sub_a1 = p("cat_a_sub1", "Sub A1", cat_a)
        leaf("a1_1", "A1 Field 1", f"A1F1-{self._suffix}", sub_a1)
        leaf("a1_2", "A1 Field 2", f"A1F2-{self._suffix}", sub_a1)
        leaf("a1_3", "A1 Field 3", f"A1F3-{self._suffix}", sub_a1)
        sub_a2 = p("cat_a_sub2", "Sub A2", cat_a)
        leaf("a2_1", "A2 Field 1", f"A2F1-{self._suffix}", sub_a2)
        leaf("a2_2", "A2 Field 2", f"A2F2-{self._suffix}", sub_a2)
        leaf("a2_3", "A2 Field 3", f"A2F3-{self._suffix}", sub_a2)

        # Category B -> SubB1 -> leaves (total 5)
        cat_b = p("cat_b", "Category B", root)
        sub_b1 = p("cat_b_sub1", "Sub B1", cat_b)
        leaf("b1_1", "B1 Field 1", f"B1F1-{self._suffix}", sub_b1)
        leaf("b1_2", "B1 Field 2", f"B1F2-{self._suffix}", sub_b1)
        leaf("b1_3", "B1 Field 3", f"B1F3-{self._suffix}", sub_b1)
        leaf("b1_4", "B1 Field 4", f"B1F4-{self._suffix}", sub_b1)
        leaf("b1_5", "B1 Field 5", f"B1F5-{self._suffix}", sub_b1)

        # Category C -> SubC1 -> leaves (total 5)
        cat_c = p("cat_c", "Category C", root)
        sub_c1 = p("cat_c_sub1", "Sub C1", cat_c)
        leaf("c1_1", "C1 Field 1", f"C1F1-{self._suffix}", sub_c1)
        leaf("c1_2", "C1 Field 2", f"C1F2-{self._suffix}", sub_c1)
        leaf("c1_3", "C1 Field 3", f"C1F3-{self._suffix}", sub_c1)
        leaf("c1_4", "C1 Field 4", f"C1F4-{self._suffix}", sub_c1)
        leaf("c1_5", "C1 Field 5", f"C1F5-{self._suffix}", sub_c1)

        # Total leaves: 6 + 5 + 5 = 16 (>=14), depth >= 3.
        return root


if __name__ == "__main__":
    # Minimal runnable demo
    logging.basicConfig(level=logging.INFO)
    app = QApplication(sys.argv)

    # Build manager with two mock sources
    manager = ComparatorManager()
    manager.sources = [
        _MockAdapter(name="Source A", values_suffix="A"),
        _MockAdapter(name="Source B", values_suffix="B"),
    ]
    manager.get_compare_data()
    manager.compare()

    # Host widget containing the tree view
    host = QWidget()
    layout = QVBoxLayout(host)
    tree = ComparatorTreeView(manager=manager, parent=host)
    layout.addWidget(tree)
    host.resize(900, 600)
    host.setWindowTitle("Comparator Tree Demo")
    host.show()

    sys.exit(app.exec_())
