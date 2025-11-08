import os
from typing import Callable, List, Optional

import pytest
from PyQt5.QtWidgets import QApplication

from exdrf_qt.comparator.logic.adapter import ComparatorAdapter
from exdrf_qt.comparator.logic.manager import ComparatorManager
from exdrf_qt.comparator.logic.nodes import LeafNode, ParentNode, Value
from exdrf_qt.context import LocalSettings, QtContext

# Ensure headless Qt on CI/CLI runs.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qt_app():
    """Ensure a single QApplication exists for Qt-based tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def manager_factory() -> Callable[[Optional[List[str]]], ComparatorManager]:
    """Factory that builds a ComparatorManager with 3 test adapters by default.

    The adapters generate a consistent tree, with a mix of equal, partial,
    different, and missing values to exercise UI and logic.
    """

    class TestAdapter(ComparatorAdapter):
        def __init__(self, name: str, code: str) -> None:
            self.name = name
            self._code = code  # 'A', 'B', 'C'

        def get_compare_data(self, mng: "ComparatorManager") -> "ParentNode":
            root = ParentNode(
                manager=mng,
                key="root",
                label=f"Root {self.name}",
            )

            def leaf(key: str, label: str, value: object, parent: ParentNode):
                lf = LeafNode(manager=mng, key=key, label=label, parent=parent)
                lf.values = [
                    Value(
                        exists=True,
                        value=value,
                        node=lf,
                        source=self,
                    )
                ]
                parent.add_child(lf)

            # Direct leaves under root:
            # - Equal across all
            leaf("k_equal", "Equal Field", "SAME", root)

            # - Partial (similar between A and B, identical A and C)
            #   A: "abc", B: "abx", C: "abc"
            if self._code == "A":
                leaf("k_partial", "Partial Field", "abc", root)
            elif self._code == "B":
                leaf("k_partial", "Partial Field", "abx", root)
            else:
                leaf("k_partial", "Partial Field", "abc", root)

            # - Different across all sources
            leaf("k_diff", "Diff Field", f"D-{self._code}", root)

            # - Present only in first source
            if self._code == "A":
                leaf("only_first", "Only First", "ONLY-A", root)

            # Nested group with mixed values
            grp = ParentNode(manager=mng, key="grp", label="Group", parent=root)
            root.add_child(grp)
            leaf("nested_equal", "Nested Equal", 42, grp)
            # Present only in second source
            if self._code == "B":
                leaf("nested_missing", "Nested Missing", "ONLY-B", grp)

            return root

    def _build(names: Optional[List[str]] = None) -> ComparatorManager:
        mgr = ComparatorManager()
        if not names:
            names = ["Source A", "Source B", "Source C"]
        codes = ["A", "B", "C"][: len(names)]
        mgr.sources = [TestAdapter(n, c) for n, c in zip(names, codes)]
        mgr.get_compare_data()
        mgr.compare()
        return mgr

    return _build


@pytest.fixture
def context(qt_app) -> QtContext:
    """Minimal QtContext for widgets that expect it."""
    return QtContext(
        c_string="",
        stg=LocalSettings(),
        top_widget=None,  # type: ignore[arg-type]
        schema=os.environ.get("EXDRF_DB_SCHEMA", "public"),
    )
