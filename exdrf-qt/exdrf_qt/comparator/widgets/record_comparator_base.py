"""Base widget for compare/merge (cmp) UIs: tree, webview, optional result
preview.

Mode is set at construction and is immutable (compare-only or merge).
Subclasses set sources (adapters) and may add a result-preview pane in
merge mode.
"""

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Sequence,
    Type,
)

from PySide6.QtWidgets import (
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from exdrf_qt.comparator.logic.adapter import ComparatorAdapter
from exdrf_qt.comparator.widgets.cmp_result_preview_pane import (
    CmpResultPreviewPane,
)
from exdrf_qt.comparator.widgets.record_to_node_adapter import (
    RecordToNodeAdapter,
)
from exdrf_qt.comparator.widgets.tree import ComparatorTreeView
from exdrf_qt.comparator.widgets.webview import ComparatorWebView
from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from exdrf_qt.comparator.logic.manager import ComparatorManager
    from exdrf_qt.context import QtContext
    from exdrf_qt.controls.templ_viewer.templ_viewer import RecordTemplViewer


class RecordComparatorBase(QWidget, QtUseContext):
    """Base widget for compare/merge (cmp) UIs: tree, webview, optional result
    preview.

    Mode is set at construction and is immutable (compare-only or merge).
    Subclasses set sources (adapters) and may add a result-preview pane in
    merge mode.

    Attributes:
        ctx: Qt context for i18n and icons.
        _merge_enabled: Whether merge mode is on (immutable).
        _manager: Comparator manager instance.
        _tree: Tree view widget.
        _webview: Web view for comparison display.
        _tabs: Tab widget containing tree, webview, and optional result pane.
        _result_preview_widget: Optional widget for result preview tab (merge
            mode).
        _record_ids: Optional sequence of record IDs (for subclasses).
    """

    ctx: "QtContext"
    _merge_enabled: bool
    _manager: "ComparatorManager"
    _tree: "ComparatorTreeView"
    _webview: "ComparatorWebView"
    _tabs: "QTabWidget"
    _result_preview_widget: Optional[QWidget]
    _record_ids: Optional[Sequence[Any]]

    def __init__(
        self,
        ctx: "QtContext",
        parent: Optional[QWidget] = None,
        *,
        merge_enabled: bool = False,
        record_ids: Optional[Sequence[Any]] = None,
    ) -> None:
        """Initialize the comparator widget.

        Args:
            ctx: Qt context for i18n and icons.
            parent: Optional parent widget.
            merge_enabled: If True, merge mode (method/result editing, result
                column); if False, compare-only. Cannot be changed after
                construction.
            record_ids: Optional sequence of record IDs for subclasses.
        """
        from exdrf_qt.comparator.logic.manager import ComparatorManager

        super().__init__(parent)
        self.ctx = ctx
        self._merge_enabled = merge_enabled
        self._manager = ComparatorManager()

        # Ensure at least one source so webview's compare() does not assert.
        if not self._manager.sources:
            self._manager.sources = [
                RecordToNodeAdapter(name="?", get_leaf_data=lambda: [])
            ]
        self._result_preview_widget = None
        self._record_ids = record_ids

        # Create tree and webview widgets.
        self._tree = ComparatorTreeView(
            self._manager,
            parent=self,
            merge_enabled=merge_enabled,
        )
        self._webview = ComparatorWebView(
            ctx=ctx,
            manager=self._manager,
            parent=self,
            merge_enabled=merge_enabled,
        )

        # Assemble tabs and add result preview in merge mode.
        self._tabs = QTabWidget(self)
        self._tabs.addTab(
            self._tree,
            self.t("cmp.tab.tree", "Properties"),
        )
        self._tabs.addTab(self._webview, self.t("cmp.tab.web", "Differences"))

        if merge_enabled:
            self._result_preview_widget = CmpResultPreviewPane(
                get_context=self.get_result_preview_context,
                parent=self,
            )
            self._tabs.addTab(
                self._result_preview_widget,
                self.t("cmp.tab.result", "Result"),
            )
            self._tabs.currentChanged.connect(self._on_tab_changed)

        # Add tabs to main layout.
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._tabs)

    def _on_tab_changed(self, index: int) -> None:
        """When the Result tab is selected, refresh the preview pane."""
        if (
            self._result_preview_widget is not None
            and self._tabs.indexOf(self._result_preview_widget) == index
            and hasattr(self._result_preview_widget, "refresh")
        ):
            self._result_preview_widget.refresh()

    def set_sources(self, adapters: List[ComparatorAdapter]) -> None:
        """Set the comparator sources and refresh the comparison.

        Args:
            adapters: List of adapters; each provides one column of data.
        """
        self._manager.sources = list(adapters)
        self.refresh_compare()

    def refresh_compare(self) -> None:
        """Reload compare data, run comparison, and refresh tree and webview."""
        self._manager.get_compare_data()
        self._manager.compare()
        self._tree.refresh()
        self._webview.refresh()

    def get_merged_payload(self) -> Dict[str, Any]:
        """Return flat key-path -> resolved value for merge mode.

        Only meaningful when merge_enabled is True. Delegates to the manager.

        Returns:
            Dict mapping dotted key path to resolved value.
        """
        return self._manager.get_merged_payload()

    def get_result_preview_context(self) -> Dict[str, Any]:
        """Return context suitable for rendering the merged result (e.g.
        template).

        Default: merged payload as a flat dict. Override to add structure or
        template-specific keys.

        Returns:
            Dict usable as template context for the result preview pane.
        """
        return self.get_merged_payload()

    def set_result_preview_widget(self, widget: Optional[QWidget]) -> None:
        """Set the result-preview widget and add a tab for it (merge mode only).

        Args:
            widget: Widget to show in a "Result" tab; None to remove.
        """
        if self._result_preview_widget is not None:
            self._tabs.removeTab(
                self._tabs.indexOf(self._result_preview_widget)
            )
            self._result_preview_widget = None
        if widget is not None and self._merge_enabled:
            self._result_preview_widget = widget
            self._tabs.addTab(widget, self._tab_label_result())

    @property
    def merge_enabled(self) -> bool:
        """Whether merge mode is on (immutable)."""
        return self._merge_enabled

    def get_viewer_class(self) -> Type["RecordTemplViewer"]:
        """Return the class for the viewer widget."""
        raise NotImplementedError("get_viewer_class not implemented")
