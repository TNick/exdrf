from __future__ import annotations

import logging
import sys
from typing import Any, Dict, Optional, Set

from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QMenu,
    QTabWidget,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from exdrf_qt.comparator.logic.adapter import ComparatorAdapter
from exdrf_qt.comparator.logic.manager import ComparatorManager
from exdrf_qt.comparator.logic.nodes import (
    BaseNode,
    LeafNode,
    ParentNode,
    Value,
)
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

        # Expand only branches that contain differences.
        self.expand_diff_branches()

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
        self.expand_diff_branches()

    # Expansion helpers
    # --------------------------------------------------------------------- #
    def expand_diff_branches(self) -> None:
        """Expand items that have differences; collapse equal branches."""
        self.collapseAll()

        def has_leaf_diff(node) -> bool:
            if not isinstance(node, LeafNode):
                return False
            # If any value missing from a source => difference.
            if any((not v.exists) for v in node.values):
                return True
            # If all values equal (including all None) => no difference.
            vals = [v.value for v in node.values]
            if not vals:
                return False
            first = vals[0]
            return any(v != first for v in vals[1:])

        def walk(parent_index):
            any_diff = False
            rows = self._model.rowCount(parent_index)
            for r in range(rows):
                idx = self._model.index(r, 0, parent_index)
                node = idx.internalPointer()
                # Difference at this node if leaf differs or any child differs.
                leaf_diff = has_leaf_diff(node)
                child_diff = False
                if self._model.rowCount(idx) > 0:
                    child_diff = walk(idx)
                node_diff = leaf_diff or child_diff
                if node_diff:
                    self.setExpanded(idx, True)
                any_diff = any_diff or node_diff
            return any_diff

        walk(self._model.index(-1, -1))  # equivalent to QModelIndex()

    # Context menu
    # --------------------------------------------------------------------- #
    def contextMenuEvent(self, event) -> None:  # type: ignore[override]
        """Show context menu with expand/collapse and copy options."""
        menu = QMenu(self)

        act_expand_all = QAction("Expand all", self)
        act_expand_all.triggered.connect(self.expandAll)
        menu.addAction(act_expand_all)

        act_expand_diff = QAction("Expand differences", self)
        act_expand_diff.triggered.connect(self.expand_diff_branches)
        menu.addAction(act_expand_diff)

        act_collapse_all = QAction("Collapse all", self)
        act_collapse_all.triggered.connect(self.collapseAll)
        menu.addAction(act_collapse_all)

        menu.addSeparator()

        # Copy as YAML (selection only) and Copy ALL as YAML.
        sel_model = self.selectionModel()
        sel = sel_model.selectedIndexes() if sel_model else []
        has_sel = any(i.column() == 0 for i in sel)

        act_copy_yaml = QAction("Copy selection as YAML", self)
        act_copy_yaml.triggered.connect(self.copy_selection_as_yaml)
        act_copy_yaml.setEnabled(has_sel)
        menu.addAction(act_copy_yaml)

        act_copy_all = QAction("Copy all as YAML", self)
        act_copy_all.triggered.connect(self.copy_all_as_yaml)
        menu.addAction(act_copy_all)

        menu.exec_(event.globalPos())

    def copy_selection_as_yaml(self) -> None:
        """Copy selected subtree(s) as YAML to the clipboard.

        If no selection, copy the entire tree.
        """
        # Collect unique top-level indexes (column 0) from selection.
        sel_model = self.selectionModel()
        sel = sel_model.selectedIndexes() if sel_model is not None else []
        rows = sorted({i.row() for i in sel if i.column() == 0})
        parent_map: Dict[Any, Set[int]] = {}
        for i in sel:
            if i.column() == 0:
                parent_map.setdefault(i.parent(), set()).add(i.row())

        items = []
        if rows and len(parent_map) == 1:
            # Same parent; export each selected row under that parent.
            parent_index = next(iter(parent_map.keys()))
            for r in rows:
                idx = self._model.index(r, 0, parent_index)
                node = idx.internalPointer()
                items.append(self._node_to_obj(node))
        else:
            # No selection or mixed parents -> export whole root.
            items.append(self._node_to_obj(self._model.root))

        yaml_str = self._to_yaml(items if len(items) > 1 else items[0])
        cb = QApplication.clipboard()
        if cb is not None:
            cb.setText(yaml_str)

    def copy_all_as_yaml(self) -> None:
        """Copy the entire tree as YAML to the clipboard."""
        obj = self._node_to_obj(self._model.root)
        yaml_str = self._to_yaml(obj)
        cb = QApplication.clipboard()
        if cb is not None:
            cb.setText(yaml_str)

    # Serialization helpers
    # --------------------------------------------------------------------- #
    def _node_to_obj(self, node):
        """Convert a node to a serializable structure for YAML."""
        if isinstance(node, LeafNode):
            values = []
            for idx, src in enumerate(self._manager.sources):
                name = getattr(src, "name", src.__class__.__name__)
                val_obj = None
                if idx < len(node.values):
                    val = node.values[idx]
                    val_obj = {
                        "source": name,
                        "exists": bool(val.exists),
                        "value": val.value,
                    }
                else:
                    val_obj = {"source": name, "exists": False, "value": None}
                values.append(val_obj)
            return {
                "type": "leaf",
                "key": node.key,
                "label": node.label,
                "values": values,
            }
        elif isinstance(node, ParentNode):
            return {
                "type": "parent",
                "key": node.key,
                "label": node.label,
                "children": [self._node_to_obj(ch) for ch in node.children],
            }
        else:
            return {"type": "node", "key": node.key, "label": node.label}

    def _to_yaml(self, obj, indent: int = 0) -> str:
        """Tiny YAML serializer for dict/list/scalars."""
        ind = "  " * indent
        if isinstance(obj, dict):
            lines = []
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    lines.append(f"{ind}{k}:")
                    lines.append(self._to_yaml(v, indent + 1))
                else:
                    s = self._scalar_to_yaml(v)
                    lines.append(f"{ind}{k}: {s}")
            return "\n".join(lines)
        if isinstance(obj, list):
            lines = []
            for item in obj:
                if isinstance(item, (dict, list)):
                    lines.append(f"{ind}-")
                    lines.append(self._to_yaml(item, indent + 1))
                else:
                    s = self._scalar_to_yaml(item)
                    lines.append(f"{ind}- {s}")
            return "\n".join(lines)
        return f"{ind}{self._scalar_to_yaml(obj)}"

    def _scalar_to_yaml(self, v) -> str:
        """Format a scalar as YAML-friendly string."""
        if v is None:
            return "null"
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, (int, float)):
            return str(v)
        s = str(v)
        # Quote if it contains special chars.
        if any(ch in s for ch in [":", "-", "#", '"', "'"]) or s.strip() != s:
            s = s.replace('"', '\\"')
            return f'"{s}"'
        return s


class FuzzyParentNode(ParentNode):
    """Parent node that implements a fuzzy compare scoring for demo purposes.

    Scoring:
      - -1: perfect match (exact key equality)
      - 80: keys equal after normalization (lower, strip non-alpha-numeric)
      - 50: labels equal after normalization
      - >0: length of common prefix of normalized keys (greedy tie-breaker)
      - 0: not similar
    """

    def compare(self, first: "BaseNode", second: "BaseNode") -> int:
        if first.key == second.key:
            return -1

        def norm(s: str) -> str:
            return "".join(ch for ch in str(s).lower() if ch.isalnum())

        k1 = norm(first.key)
        k2 = norm(second.key)
        if k1 and k1 == k2:
            return 80

        l1 = norm(first.label)
        l2 = norm(second.label)
        if l1 and l1 == l2:
            return 50

        # Common prefix length of normalized keys.
        common = 0
        for a, b in zip(k1, k2):
            if a == b:
                common += 1
            else:
                break
        return common


class _MockAdapter(ComparatorAdapter):
    """Simple in-memory adapter for demo purposes."""

    def __init__(self, name: str, values_suffix: str) -> None:
        self.name = name
        self._suffix = values_suffix

    def get_compare_data(self, mng: "ComparatorManager") -> "ParentNode":
        # Helper factories
        def p(key: str, label: str, parent: ParentNode) -> ParentNode:
            node = FuzzyParentNode(
                manager=mng, key=key, label=label, parent=parent
            )
            parent.add_child(node)
            return node

        def _tweak_key(original_key: str) -> str:
            """Introduce key variations for Source B."""
            if self._suffix != "B":
                return original_key
            if original_key == "a1_2":
                return "a1-2"
            if original_key.startswith("a2_"):
                return original_key.replace("_", "-")
            if original_key == "b1_4":
                return "b1-4"
            return original_key

        def _value_for(original_key: str, base_code: str) -> str:
            """Produce the value text, forcing equality on a few demo leaves."""
            equal_keys = {"a1_3", "c1_5"}
            if original_key in equal_keys:
                return base_code
            return f"{base_code}-{self._suffix}"

        def _red_demo_value(original_key: str) -> str:
            """Produce a pair of similar-but-different strings to trigger
            inline diff highlighting in the UI.
            """
            if original_key != "c1_6":
                return ""
            if self._suffix == "A":
                return "This is some bullshit"
            return "Not similar at all"

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
        root = FuzzyParentNode(
            manager=mng, key="root", label=f"Root {self.name}"
        )

        # Category A -> SubA1/SubA2 -> leaves (total 6)
        cat_a = p("cat_a", "Category A", root)
        sub_a1 = p("cat_a_sub1", "Sub A1", cat_a)
        leaf(_tweak_key("a1_1"), "A1 Field 1", f"A1F1-{self._suffix}", sub_a1)
        leaf(_tweak_key("a1_2"), "A1 Field 2", f"A1F2-{self._suffix}", sub_a1)
        leaf(
            _tweak_key("a1_3"),
            "A1 Field 3",
            _value_for("a1_3", "A1F3"),
            sub_a1,
        )
        sub_a2_key = "cat_a_sub2" if self._suffix != "B" else "cat_a_sub_2"
        sub_a2_label = "Sub A2" if self._suffix != "B" else "Sub A-2"
        sub_a2 = p(sub_a2_key, sub_a2_label, cat_a)
        leaf(_tweak_key("a2_1"), "A2 Field 1", f"A2F1-{self._suffix}", sub_a2)
        leaf(_tweak_key("a2_2"), "A2 Field 2", f"A2F2-{self._suffix}", sub_a2)
        leaf(_tweak_key("a2_3"), "A2 Field 3", f"A2F3-{self._suffix}", sub_a2)

        # Category B -> SubB1 -> leaves (total 5)
        cat_b_label = "Category B" if self._suffix != "B" else "Category Bee"
        cat_b = p("cat_b", cat_b_label, root)
        sub_b1 = p("cat_b_sub1", "Sub B1", cat_b)
        leaf(_tweak_key("b1_1"), "B1 Field 1", f"B1F1-{self._suffix}", sub_b1)
        leaf(_tweak_key("b1_2"), "B1 Field 2", f"B1F2-{self._suffix}", sub_b1)
        leaf(_tweak_key("b1_3"), "B1 Field 3", f"B1F3-{self._suffix}", sub_b1)
        leaf(_tweak_key("b1_4"), "B1 Field 4", f"B1F4-{self._suffix}", sub_b1)
        leaf(_tweak_key("b1_5"), "B1 Field 5", f"B1F5-{self._suffix}", sub_b1)

        # Category C -> SubC1 -> leaves (total 5)
        cat_c = p("cat_c", "Category C", root)
        sub_c1 = p("cat_c_sub1", "Sub C1", cat_c)
        leaf(_tweak_key("c1_1"), "C1 Field 1", f"C1F1-{self._suffix}", sub_c1)
        leaf(_tweak_key("c1_2"), "C1 Field 2", f"C1F2-{self._suffix}", sub_c1)
        leaf(_tweak_key("c1_3"), "C1 Field 3", f"C1F3-{self._suffix}", sub_c1)
        leaf(_tweak_key("c1_4"), "C1 Field 4", f"C1F4-{self._suffix}", sub_c1)
        leaf(
            _tweak_key("c1_5"),
            "C1 Field 5",
            _value_for("c1_5", "C1F5"),
            sub_c1,
        )
        # Extra demo pair: similar strings that exceed similarity threshold
        # and will show inline character differences.
        leaf(
            _tweak_key("c1_6"),
            "C1 Field 6",
            _red_demo_value("c1_6"),
            sub_c1,
        )

        # Total leaves: 6 + 5 + 5 = 16 (>=14), depth >= 3.
        return root


if __name__ == "__main__":
    # Minimal runnable demo
    logging.basicConfig(level=logging.INFO)

    # Initialize Qt WebEngine before creating QApplication
    # This must be done before QApplication is instantiated
    # Import QtWebEngineWidgets to initialize the plugin
    try:
        import PyQt5.QtWebEngineWidgets  # noqa: F401
    except ImportError:
        # If import fails, try setting the attribute instead
        try:
            from PyQt5.QtCore import QCoreApplication, Qt

            QCoreApplication.setAttribute(  # type: ignore
                Qt.AA_ShareOpenGLContexts, True  # type: ignore
            )
        except Exception:
            pass

    app = QApplication(sys.argv)

    # Build manager with three mock sources
    manager = ComparatorManager()
    manager.sources = [
        _MockAdapter(name="Source A", values_suffix="A"),
        _MockAdapter(name="Source B", values_suffix="B"),
        _MockAdapter(name="Source C", values_suffix="C"),
    ]
    manager.get_compare_data()
    manager.compare()

    # Create host widget first (needed for context)
    host = QWidget()

    # Create a minimal QtContext for the webview
    import os

    from exdrf_qt.context import LocalSettings, QtContext

    ctx = QtContext(
        c_string="",
        stg=LocalSettings(),
        top_widget=None,  # type: ignore
        schema=os.environ.get("EXDRF_DB_SCHEMA", "public"),
    )  # type: ignore
    ctx.top_widget = host  # type: ignore

    # Create layout with tabs for tree and webview
    layout = QVBoxLayout(host)

    tabs = QTabWidget(host)
    layout.addWidget(tabs)

    # Tree view tab
    tree = ComparatorTreeView(manager=manager, parent=host)
    tabs.addTab(tree, "Tree View")

    # Webview tab
    try:
        from exdrf_qt.comparator.widgets.webview import ComparatorWebView

        webview = ComparatorWebView(
            ctx=ctx, manager=manager, parent=host  # type: ignore
        )
        tabs.addTab(webview, "Web View")
    except Exception as e:
        logging.error("Failed to create webview: %s", e, exc_info=True)
        # Continue without webview if it fails

    host.resize(1200, 800)
    host.setWindowTitle("Comparator Demo - Tree & Web View")
    host.show()

    sys.exit(app.exec_())
