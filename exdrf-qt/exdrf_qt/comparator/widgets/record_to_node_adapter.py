"""Adapter that builds a comparator ParentNode from a list of (key, label, value).

Used by generated cmp widgets to turn each record into one comparison column.
"""

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Optional,
    Sequence,
    Tuple,
)

from exdrf_qt.comparator.logic.adapter import ComparatorAdapter
from exdrf_qt.comparator.logic.nodes import (
    LeafNode,
    ParentNode,
    Value,
)

if TYPE_CHECKING:
    from exdrf_qt.comparator.logic.manager import ComparatorManager

LeafDataItem = Tuple[str, str, Any]
LeafDataCallable = Callable[[], Sequence[LeafDataItem]]


class RecordToNodeAdapter(ComparatorAdapter):
    """Adapter that builds a comparator ParentNode from a list of (key, label,
    value).

    Used by generated cmp widgets to turn each record into one comparison
    column.

    Attributes:
        name: Display name for this source (e.g. "Record 1", "Item A").
        _get_leaf_data: Callable returning (key, label, value) sequence to
            build leaf nodes. Key must be stable across sources.
    """

    name: str
    _get_leaf_data: LeafDataCallable

    def __init__(
        self,
        name: str,
        get_leaf_data: LeafDataCallable,
    ) -> None:
        """Build an adapter that returns a tree from get_leaf_data().

        Args:
            name: Display name for this source (e.g. "Record 1", "Item A").
            get_leaf_data: Callable returning a sequence of (key, label, value)
                used to build leaf nodes. Key must be stable across sources.
        """
        self.name = name
        self._get_leaf_data = get_leaf_data

    def get_compare_data(self, mng: "ComparatorManager") -> ParentNode:
        """Return a root ParentNode whose children are leaves from get_leaf_data.

        Args:
            mng: The comparator manager.

        Returns:
            A root ParentNode whose children are leaves from get_leaf_data.
        """
        root = ParentNode(manager=mng)

        # Build a leaf node for each (key, label, value) tuple.
        for key, label, value in self._get_leaf_data():
            leaf = LeafNode(
                manager=mng,
                key=key,
                label=label,
                parent=root,
            )
            leaf.values.append(
                Value(
                    exists=True,
                    value=value,
                    node=leaf,
                    source=self,
                )
            )
            root.add_child(leaf)
        return root

    def get_merge_item_label(
        self, mng: "ComparatorManager", source_index: int
    ) -> Optional[str]:
        """Use this adapter's name as the merge list label."""
        return self.name
