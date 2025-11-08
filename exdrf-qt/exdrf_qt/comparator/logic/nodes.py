from typing import Any, List, TYPE_CHECKING, Optional
from attrs import define, field

if TYPE_CHECKING:
    from exdrf_qt.comparator.logic.manager import ComparatorManager
    from exdrf_qt.comparator.logic.adapter import ComparatorAdapter


@define
class BaseNode:
    """Represents the common base class for all nodes in the comparator.

    Attributes:
        manager: The manager that this node belongs to.
        label: The label of this node.
        parent: The parent node of this node. For root nodes, this is None.
    """

    manager: "ComparatorManager"
    key: str = field(default="")
    label: str = field(default="")
    parent: Optional["BaseNode"] = field(default=None)

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


@define
class ParentNode(BaseNode):
    """Represents a node that does not have its own value but can host other
    nodes.
    """

    children: List["BaseNode"] = field(factory=list)

    def add_child(self, child: "BaseNode") -> None:
        """Add a child node to this parent node."""
        self.children.append(child)

    @property
    def child_count(self) -> int:
        """The number of children this node has."""
        return len(self.children)


@define
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

    @property
    def is_leaf(self) -> bool:
        """Whether this node is a leaf node."""
        return True
