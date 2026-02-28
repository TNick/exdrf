from typing import TYPE_CHECKING, Any, List, Optional

if TYPE_CHECKING:
    from exdrf_qt.comparator.logic.manager import ComparatorManager
    from exdrf_qt.comparator.logic.merge import (
        LeafMergeState,
        MergeContext,
        MergeMethodOption,
    )
    from exdrf_qt.comparator.logic.nodes import LeafNode, ParentNode


class ComparatorAdapter:
    """Defines the interface that needs to be implemented so that data can be
    extracted from a source. Optional merge hooks allow per-source or
    per-property overrides when merge mode is enabled.
    """

    def get_compare_data(self, mng: "ComparatorManager") -> "ParentNode":
        """Get the data that will be used for comparison.

        Args:
            mng: The manager that this adapter belongs to.

        Returns:
            A single parent node that will not be used in the comparison but
            will be used only as a container for the data.
        """
        raise NotImplementedError("get_compare_data")

    # Optional merge hooks (return None to use strategy default).
    # -------------------------------------------------------------------------

    def get_merge_item_label(
        self, mng: "ComparatorManager", source_index: int
    ) -> Optional[str]:
        """Return the display label for one item/source in merge method list.

        Args:
            mng: The comparator manager.
            source_index: Zero-based index of the source (0 = Item 1, etc.).

        Returns:
            Label string for this source, or None to use strategy default
            (e.g. "Item 1", "Item 2").
        """
        return None

    def get_available_merge_methods_for_leaf(
        self, mng: "ComparatorManager", leaf: "LeafNode"
    ) -> Optional[List["MergeMethodOption"]]:
        """Return merge methods allowed for this leaf, or None to use strategy.

        Args:
            mng: The comparator manager.
            leaf: The leaf node (key/label identify the property).

        Returns:
            List of method options, or None to use manager strategy default.
        """
        return None

    def create_merge_editor(
        self,
        parent: Any,
        context: "MergeContext",
        state: "LeafMergeState",
        current_value: Any,
    ) -> Optional[Any]:
        """Create a custom editor widget for the merge result cell, or None.

        Args:
            parent: Parent Qt widget for the editor.
            context: Merge context for the leaf.
            state: Current merge state.
            current_value: Current value to show in the editor.

        Returns:
            Editor widget, or None to use default (e.g. line edit for manual).
        """
        return None
