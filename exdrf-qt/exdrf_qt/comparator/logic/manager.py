from attrs import define, field
from typing import List, TYPE_CHECKING
from exdrf_qt.comparator.logic.adapter import ComparatorAdapter


if TYPE_CHECKING:
    from exdrf_qt.comparator.logic.nodes import BaseNode, ParentNode


@define
class ComparatorManager:
    """Manages the comparison between two or more items.

    Attributes:
        sources: List of sources that will be queried for comparison.
    """

    sources: List["ComparatorAdapter"] = field(factory=list)
    root: "ParentNode" = field(default=None)
    data: List["BaseNode"] = field(factory=list)

    def __attrs_post_init__(self) -> None:
        """Post-initialization hook."""
        from exdrf_qt.comparator.logic.nodes import ParentNode

        self.root = ParentNode(manager=self)

    def get_compare_data(self) -> List["BaseNode"]:
        """Get the data that will be used for comparison."""
        self.data = [adapter.get_compare_data(self) for adapter in self.sources]
        return self.data

    def compare(self) -> None:
        """Compare all source trees and populate `root` with a merged tree.

        The merge aligns nodes by their `key` (falling back to `label` if key
        is empty). For each aligned set:
        - If any corresponding node is a parent, a parent is created and
          children are merged recursively.
        - Otherwise, a leaf is created with `values` sized to number of sources,
          each entry marked with `exists=True/False` and bound to the
          appropriate source.
        """
        from exdrf_qt.comparator.logic.nodes import ParentNode, LeafNode, Value

        # Ensure data is present.
        if not self.data:
            self.get_compare_data()

        # Reset root.
        self.root = ParentNode(manager=self)

        # Helper: build a mapping key -> list[(src_idx, node)]
        def group_children(parents: List["ParentNode"]):
            merged: dict[str, List[tuple[int, "BaseNode"]]] = {}
            for src_idx, p in enumerate(parents):
                if not isinstance(p, ParentNode):
                    continue
                for ch in getattr(p, "children", []):
                    k = ch.key or ch.label
                    merged.setdefault(k, []).append((src_idx, ch))
            return merged

        # Recursive merge.
        def merge(parents: List["ParentNode"], out_parent: "ParentNode"):
            merged = group_children(parents)
            for k in sorted(merged.keys(), key=lambda x: (x or "").lower()):
                entries = merged[k]
                has_parent = any(isinstance(n, ParentNode) for _, n in entries)
                label = next((n.label for _, n in entries if n.label), k)

                if has_parent:
                    new_p = ParentNode(
                        manager=self,
                        key=k,
                        label=label,
                        parent=out_parent,
                    )
                    out_parent.add_child(new_p)
                    # For missing sources, use a dummy empty parent.
                    per_src_parents: List["ParentNode"] = []
                    for idx in range(len(self.sources)):
                        found = next(
                            (n for i, n in entries if i == idx),
                            None,
                        )
                        if isinstance(found, ParentNode):
                            per_src_parents.append(found)
                        else:
                            per_src_parents.append(
                                ParentNode(
                                    manager=self,
                                    key=k,
                                    label=label,
                                )
                            )
                    merge(per_src_parents, new_p)
                else:
                    # Create a leaf with values aligned to self.sources order.
                    new_l = LeafNode(
                        manager=self,
                        key=k,
                        label=label,
                        parent=out_parent,
                    )
                    values: List["Value"] = []
                    for idx in range(len(self.sources)):
                        found = next(
                            (
                                n
                                for i, n in entries
                                if i == idx and isinstance(n, LeafNode)
                            ),
                            None,
                        )
                        if isinstance(found, LeafNode) and found.values:
                            # Use the first provided value from that source.
                            raw_val = (
                                found.values[0].value
                                if hasattr(found.values[0], "value")
                                else None
                            )
                            values.append(
                                Value(
                                    exists=True,
                                    value=raw_val,
                                    node=new_l,
                                    source=self.sources[idx],
                                )
                            )
                        else:
                            values.append(
                                Value(
                                    exists=False,
                                    value=None,
                                    node=new_l,
                                    source=self.sources[idx],
                                )
                            )
                    new_l.values = values
                    out_parent.add_child(new_l)

        # Kick off merging from each per-source root.
        src_roots: List["ParentNode"] = []
        for node in self.data:
            if isinstance(node, ParentNode):
                src_roots.append(node)
        merge(src_roots, self.root)
