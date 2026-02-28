from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

from attrs import define, field

from exdrf_qt.comparator.logic.adapter import ComparatorAdapter

if TYPE_CHECKING:
    from exdrf_qt.comparator.logic.merge import (
        MergeContext,
        MergeMethodOption,
        MergeStrategy,
    )
    from exdrf_qt.comparator.logic.nodes import BaseNode, LeafNode, ParentNode


@define(eq=False)
class ComparatorManager:
    """Manages the comparison between two or more items.

    When merge mode is enabled, merge_strategy and adapter hooks control
    method labels, available methods, and value resolution.

    Attributes:
        sources: List of sources that will be queried for comparison.
        root: Unified root node after compare().
        data: Per-source roots from get_compare_data().
        merge_strategy: Optional merge strategy; None uses default behavior.
    """

    sources: List["ComparatorAdapter"] = field(factory=list)
    root: "ParentNode" = field(default=None, repr=False)
    data: List["BaseNode"] = field(factory=list)
    merge_strategy: Optional["MergeStrategy"] = field(default=None)

    def __attrs_post_init__(self) -> None:
        """Post-initialization hook."""
        from exdrf_qt.comparator.logic.nodes import ParentNode

        self.root = ParentNode(manager=self)

    def get_compare_data(self) -> List["BaseNode"]:
        """Get the data that will be used for comparison."""
        self.data = [adapter.get_compare_data(self) for adapter in self.sources]
        return self.data

    def compare(self) -> None:
        from exdrf_qt.comparator.logic.nodes import LeafNode, ParentNode, Value

        stack = [
            {
                "src": self.data,
                "dst": self.root,
            }
        ]

        while stack:
            frame = stack.pop()

            sources = cast(List["ParentNode | None"], frame["src"])
            destination = cast("ParentNode", frame["dst"])

            children: List[Dict[int, "BaseNode"]] = []
            is_first = True
            for s_i, source in enumerate(sources):
                if source is None:
                    continue

                if is_first:
                    # The first source simply adds all its children to the
                    # destination.
                    is_first = False

                    for child in source.children:
                        children.append({s_i: child})
                else:
                    # Other sources must either match one of the existing
                    # children or create a new child.

                    # We start by creating a matrix of scores, one for each
                    # child and source.
                    len_c = len(children)
                    scores = [[0] * len_c for _ in range(len(source.children))]
                    for o_i, other_data in enumerate(children):
                        # Get the data from the first source that provided data
                        # for this child.
                        other = other_data[min(other_data.keys())]
                        # Now go through the current source's children and
                        # compare them to the other child.
                        for crt_i, current in enumerate(source.children):
                            scores[crt_i][o_i] = (
                                0
                                if (other.is_leaf != current.is_leaf)
                                else source.compare(other, current)
                            )

                    # Now we need to find the best match for each child in the
                    # order of the score, while making sure that we don't match
                    # the same child to multiple sources. -1 means a perfect
                    # match and is evaluated first, 0 means never match,
                    # others are evaluated in order of similarity but the
                    # order is absolute across the board., so the highest
                    # score left on the board should be pulled, make that
                    # association and repeat until there are no more matches.

                    # Prepare greedy matching with priority:
                    # 1) Perfect matches (-1) first
                    # 2) Then scores in descending order
                    row_count = len(source.children)
                    col_count = len_c

                    # Track used rows/cols to avoid duplicate matches.
                    used_rows: set[int] = set()
                    used_cols: set[int] = set()

                    # First, take all perfect matches.
                    for r in range(row_count):
                        for c in range(col_count):
                            if (
                                scores[r][c] == -1
                                and r not in used_rows
                                and c not in used_cols
                            ):
                                # Assign this perfect pair.
                                children[c][s_i] = source.children[r]
                                used_rows.add(r)
                                used_cols.add(c)

                    # Next, consider all scores and pick highest first.
                    candidates: List[tuple[int, int, int]] = []
                    for r in range(row_count):
                        for c in range(col_count):
                            sc = scores[r][c]
                            if sc != 0 and sc != -1:
                                candidates.append((sc, r, c))

                    # Sort by score descending.
                    candidates.sort(key=lambda t: t[0], reverse=True)

                    for sc, r, c in candidates:
                        if r in used_rows or c in used_cols:
                            continue
                        children[c][s_i] = source.children[r]
                        used_rows.add(r)
                        used_cols.add(c)

                    # Finally, any row not matched creates a new child entry.
                    for r in range(row_count):
                        if r not in used_rows:
                            children.append({s_i: source.children[r]})
            assert not is_first, "At least one source must be provided."

            # At this point for each children all values are either leafs or
            # parents or not set. Each entry will have at least one member.

            for c_data in children:
                sample = c_data[min(c_data.keys())]

                new_node: "BaseNode"
                if sample.is_leaf:
                    new_node = LeafNode(
                        manager=self,
                        key=sample.key,
                        label=sample.label,
                        parent=destination,
                    )
                    for s_i, source in enumerate(sources):
                        adapter = self.sources[s_i]
                        buddy = cast("LeafNode", c_data.get(s_i, None))
                        if buddy is not None:
                            if len(buddy.values) > 0 and buddy.values[0].exists:
                                new_node.values.append(
                                    Value(
                                        exists=True,
                                        value=buddy.values[0].value,
                                        node=new_node,
                                        source=adapter,
                                    )
                                )
                                continue

                        new_node.values.append(
                            Value(
                                exists=False,
                                value=None,
                                node=new_node,
                                source=adapter,
                            )
                        )
                else:
                    new_node = ParentNode(
                        manager=self,
                        key=sample.key,
                        label=sample.label,
                        parent=destination,
                    )
                    new_sources: List["BaseNode | None"] = []
                    for s_i, source in enumerate(sources):
                        if s_i in c_data:
                            new_sources.append(c_data[s_i])
                        else:
                            new_sources.append(None)

                    stack.append(
                        {
                            "src": new_sources,
                            "dst": new_node,
                        }
                    )
                destination.add_child(new_node)

    # Merge mode helpers (no-op if merge not used).
    # -------------------------------------------------------------------------

    def _get_strategy(self) -> "MergeStrategy":
        """Return the effective merge strategy (never None)."""
        from exdrf_qt.comparator.logic.merge import DefaultMergeStrategy

        if self.merge_strategy is not None:
            return self.merge_strategy
        return DefaultMergeStrategy()

    def get_merge_context(self, leaf: "LeafNode") -> "MergeContext":
        """Build merge context for a leaf (values and source labels).

        Args:
            leaf: The leaf node.

        Returns:
            MergeContext with values and source_labels (from adapters or
            strategy).
        """
        from exdrf_qt.comparator.logic.merge import MergeContext

        strategy = self._get_strategy()
        num_sources = len(self.sources)
        source_labels = []
        for i in range(num_sources):
            label = None
            if i < len(self.sources):
                adapter = self.sources[i]
                label = adapter.get_merge_item_label(self, i)
            if label is None:
                ctx = MergeContext(leaf=leaf, manager=self, values=leaf.values)
                labels = strategy.get_item_labels(ctx, num_sources)
                label = labels[i] if i < len(labels) else "Item %d" % (i + 1)
            source_labels.append(label)
        return MergeContext(
            leaf=leaf,
            manager=self,
            values=list(leaf.values),
            source_labels=source_labels,
        )

    def get_available_merge_methods(
        self, leaf: "LeafNode"
    ) -> List["MergeMethodOption"]:
        """Return merge methods for this leaf (adapter override or strategy).

        Args:
            leaf: The leaf node.

        Returns:
            List of method options.
        """
        for adapter in self.sources:
            opts = adapter.get_available_merge_methods_for_leaf(self, leaf)
            if opts is not None:
                return opts
        context = self.get_merge_context(leaf)
        return self._get_strategy().get_available_methods(context)

    def resolve_merge_value(self, leaf: "LeafNode") -> Any:
        """Resolve the merged value for a leaf from its merge state.

        Args:
            leaf: The leaf node (merge_state set when merge mode used).

        Returns:
            Resolved value (may be None).
        """
        from exdrf_qt.comparator.logic.merge import LeafMergeState

        state = getattr(leaf, "merge_state", None)
        if state is None:
            state = LeafMergeState()
        context = self.get_merge_context(leaf)
        resolved = self._get_strategy().resolve_value(context, state)
        if getattr(leaf, "merge_state", None) is not None:
            leaf.merge_state.resolved_value = resolved
        return resolved

    def get_merged_payload(self) -> Dict[str, Any]:
        """Walk all leaves and return flat key-path -> resolved value map.

        Keys are dotted paths from root (e.g. "grp.nested_equal"). Only leaf
        nodes are included. Merge state is initialized on leaves by the tree
        model in merge mode.

        Returns:
            Dict mapping dotted key path to resolved value.
        """
        from exdrf_qt.comparator.logic.nodes import LeafNode, ParentNode

        result: Dict[str, Any] = {}

        def walk(node: "BaseNode", path_prefix: List[str]) -> None:
            if isinstance(node, LeafNode):
                key_path = ".".join(path_prefix) if path_prefix else node.key
                result[key_path] = self.resolve_merge_value(node)
            elif isinstance(node, ParentNode):
                for child in node.children:
                    child_path = (
                        path_prefix + [child.key] if child.key else path_prefix
                    )
                    walk(child, child_path)

        if self.root is not None:
            for child in self.root.children:
                walk(child, [child.key] if child.key else [])

        return result
