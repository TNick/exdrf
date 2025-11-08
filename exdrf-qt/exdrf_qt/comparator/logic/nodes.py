from typing import TYPE_CHECKING, Any, List, Optional

from attrs import define, field

if TYPE_CHECKING:
    from exdrf_qt.comparator.logic.adapter import ComparatorAdapter
    from exdrf_qt.comparator.logic.manager import ComparatorManager


@define(eq=False)
class BaseNode:
    """Represents the common base class for all nodes in the comparator.

    Attributes:
        manager: The manager that this node belongs to.
        label: The label of this node.
        parent: The parent node of this node. For root nodes, this is None.
    """

    manager: "ComparatorManager" = field(repr=False)
    key: str = field(default="")
    label: str = field(default="")
    parent: Optional["BaseNode"] = field(default=None, repr=False)

    @property
    def is_leaf(self) -> bool:
        """Whether this node has children or contains a value."""
        return False

    @property
    def is_parent(self) -> bool:
        """Whether this node is a parent node."""
        return not self.is_leaf

    @property
    def is_root(self) -> bool:
        """Whether this node is the root node."""
        return self.parent is None

    @property
    def child_count(self) -> int:
        """The number of children this node has."""
        return 0


@define(eq=False)
class ParentNode(BaseNode):
    """Represents a node that does not have its own value but can host other
    nodes.

    Attributes:
        children: List of children nodes.
    """

    children: List["BaseNode"] = field(factory=list, repr=False)
    mismatch_count_value: int = field(default=-1)

    def add_child(self, child: "BaseNode") -> None:
        """Add a child node to this parent node."""
        self.children.append(child)

    @property
    def child_count(self) -> int:
        """The number of children this node has."""
        return len(self.children)

    def compare(self, first: "BaseNode", second: "BaseNode") -> int:
        """Compare two nodes and return a score.

        Args:
            first: The first node to compare.
            second: The second node to compare.

        Returns:
            A score that will be used to determine if the nodes are the same.
            If the value is 0, the nodes are not the same; if the value is -1,
            the nodes are the same and no other comparison is needed; any other
            value will be be used to choose a match amongst the children of
            this parent. The score should be based on the similarity of the
            nodes.
        """
        return -1 if first.key == second.key else 0

    @property
    def mismatch_count(self) -> int:
        if self.mismatch_count_value == -1:
            self.mismatch_count_value = 0
            for child in self.children:
                if isinstance(child, LeafNode):
                    if not child.are_equal:
                        self.mismatch_count_value += 1
                elif isinstance(child, ParentNode):
                    self.mismatch_count_value += child.mismatch_count
        return self.mismatch_count_value


@define(eq=False)
class Value:
    """Represents the value in a leaf node.

    Attributes:
        exists: Whether the source provided a value for this leaf node.
        value: The value of the leaf node. None is just another value.
        node: The leaf node that this value belongs to.
        source: The source that provided the value.
    """

    exists: bool
    value: Any
    node: "LeafNode"
    source: "ComparatorAdapter"


@define
class LeafNode(BaseNode):
    """Represents a node that has its own value.

    Attributes:
        values: List of values that this node contains, one for each source.
    """

    values: List[Value] = field(factory=list)
    are_equal_value: bool | None = field(default=None)

    @property
    def is_leaf(self) -> bool:
        """Whether this node is a leaf node."""
        return True

    @property
    def are_equal(self) -> bool:
        """Whether this node is equal to another node."""
        if self.are_equal_value is None:
            reference = None
            for v_i, value in enumerate(self.values):
                if v_i == 0:
                    reference = value.exists, value.value
                elif (value.exists, value.value) != reference:
                    self.are_equal_value = False
                    break
            if self.are_equal_value is None:
                self.are_equal_value = True
        return self.are_equal_value
