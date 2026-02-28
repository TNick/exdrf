"""Merge contracts and method IDs for the comparator merge workflow.

This module defines merge method constants, per-leaf merge state, method
options, merge context, and strategy/adapter hook protocols. Merge mode is
opt-in; when enabled, the tree view shows Method and Result columns and the
webview can show a Result column.
"""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    List,
    Optional,
    Protocol,
    runtime_checkable,
)

from attrs import define, field

if TYPE_CHECKING:
    from exdrf_qt.comparator.logic.manager import ComparatorManager
    from exdrf_qt.comparator.logic.nodes import LeafNode, Value

# Merge method ID constants.
MERGE_METHOD_FIRST_NOT_NULL = "first_not_null"
MERGE_METHOD_SET_NULL = "set_null"
MERGE_METHOD_MANUAL = "manual"


def merge_method_item(source_index: int) -> str:
    """Return the method ID for choosing the value from source at index.

    Args:
        source_index: Zero-based index of the source (Item 1 -> 0, etc.).

    Returns:
        String like "item:0", "item:1", etc.
    """
    return "item:%d" % source_index


def parse_item_method_id(method_id: str) -> Optional[int]:
    """Parse an item method ID into source index, or None if not item:N.

    Args:
        method_id: Method ID string, e.g. "item:0".

    Returns:
        Source index (0-based) or None.
    """
    if not method_id.startswith("item:"):
        return None
    try:
        return int(method_id[5:])
    except ValueError:
        return None


@define
class MergeMethodOption:
    """A single merge method choice shown in the UI.

    Attributes:
        id: Unique method ID (e.g. "item:0", "first_not_null", "manual").
        label: Display label (e.g. "Item 1", "First not null", "Manual").
    """

    id: str = field()
    label: str = field()


@define
class LeafMergeState:
    """Per-leaf merge state: selected method, manual value, cached result.

    Attributes:
        selected_method: Current merge method ID. Default first_not_null.
        manual_value: User-entered value when method is manual; None otherwise.
        resolved_value: Cached resolved value; None until computed.
    """

    selected_method: str = field(default=MERGE_METHOD_FIRST_NOT_NULL)
    manual_value: Any = field(default=None)
    resolved_value: Any = field(default=None)


@define
class MergeContext:
    """Context passed to strategy/adapter hooks for a single leaf.

    Attributes:
        leaf: The leaf node being merged.
        manager: The comparator manager.
        values: List of Value objects for this leaf (aligned with sources).
        source_labels: Optional display labels for each source (Item 1, etc.).
    """

    leaf: "LeafNode" = field()
    manager: "ComparatorManager" = field()
    values: List["Value"] = field(factory=list)
    source_labels: List[str] = field(factory=list)


@runtime_checkable
class MergeStrategy(Protocol):
    """Protocol for manager-level merge strategy (labels, methods, resolve)."""

    def get_item_labels(
        self, context: MergeContext, num_sources: int
    ) -> List[str]:
        """Return display labels for each source (Item 1, Item 2, ...).

        Args:
            context: Merge context for the leaf.
            num_sources: Number of sources.

        Returns:
            List of num_sources label strings.
        """
        ...

    def get_available_methods(
        self, context: MergeContext
    ) -> List[MergeMethodOption]:
        """Return the list of merge methods allowed for this leaf.

        Args:
            context: Merge context for the leaf.

        Returns:
            List of method options (id + label).
        """
        ...

    def resolve_value(
        self,
        context: MergeContext,
        state: LeafMergeState,
    ) -> Any:
        """Compute the merged value from context and current state.

        Args:
            context: Merge context for the leaf.
            state: Current merge state (method, manual value).

        Returns:
            Resolved value (may be None).
        """
        ...


@runtime_checkable
class MergeEditorFactory(Protocol):
    """Protocol for a custom editor widget for the result column.

    Used when method is manual or when implementation provides a custom
    editor. If create_editor returns None, the default (e.g. QLineEdit)
    is used.
    """

    def create_editor(
        self,
        parent: Any,
        context: MergeContext,
        state: LeafMergeState,
        current_value: Any,
    ) -> Optional[Any]:
        """Create an editor widget for the merge result cell.

        Args:
            parent: Parent Qt widget for the editor.
            context: Merge context for the leaf.
            state: Current merge state.
            current_value: Current resolved or manual value to show in editor.

        Returns:
            Editor widget or None to use default.
        """
        ...


class DefaultMergeStrategy:
    """Default merge strategy: Item 1..N, first not null, set null, manual."""

    def get_item_labels(
        self, context: MergeContext, num_sources: int
    ) -> List[str]:
        """Return default labels Item 1, Item 2, ... or context labels."""
        if context.source_labels and len(context.source_labels) >= num_sources:
            return context.source_labels[:num_sources]
        return ["Item %d" % (i + 1) for i in range(num_sources)]

    def get_available_methods(
        self, context: MergeContext
    ) -> List[MergeMethodOption]:
        """Return item:0..N, first_not_null, set_null, manual."""
        num_sources = len(context.manager.sources)
        labels = self.get_item_labels(context, num_sources)
        options: List[MergeMethodOption] = []
        for i in range(num_sources):
            options.append(
                MergeMethodOption(id=merge_method_item(i), label=labels[i])
            )
        options.append(
            MergeMethodOption(
                id=MERGE_METHOD_FIRST_NOT_NULL, label="First not null"
            )
        )
        options.append(
            MergeMethodOption(id=MERGE_METHOD_SET_NULL, label="Set to null")
        )
        options.append(
            MergeMethodOption(id=MERGE_METHOD_MANUAL, label="Manual")
        )
        return options

    def resolve_value(
        self,
        context: MergeContext,
        state: LeafMergeState,
    ) -> Any:
        """Resolve value from selected method and values."""
        method = state.selected_method
        values = context.values

        idx = parse_item_method_id(method)
        if idx is not None:
            if 0 <= idx < len(values) and values[idx].exists:
                return values[idx].value
            return None

        if method == MERGE_METHOD_SET_NULL:
            return None

        if method == MERGE_METHOD_MANUAL:
            return state.manual_value

        if method == MERGE_METHOD_FIRST_NOT_NULL:
            for v in values:
                if v.exists and v.value is not None:
                    return v.value
            return None

        return None
