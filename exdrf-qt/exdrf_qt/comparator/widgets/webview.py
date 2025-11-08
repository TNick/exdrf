"""Web-based comparator viewer widget.

This module provides a web-based comparison viewer for the general-purpose
comparator system, rendering differences in a side-by-side layout using a
Jinja-powered HTML template.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any, Dict, List

from exdrf.var_bag import VarBag

from exdrf_qt.comparator.logic.manager import ComparatorManager
from exdrf_qt.comparator.logic.nodes import LeafNode, ParentNode, Value
from exdrf_qt.context_use import QtUseContext
from exdrf_qt.controls.templ_viewer.templ_viewer import TemplViewer

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext

logger = logging.getLogger(__name__)


class ComparatorWebView(TemplViewer, QtUseContext):
    """Web-based compare viewer for the general-purpose comparator.

    This widget renders comparison data from a ComparatorManager in a
    side-by-side layout using a Jinja-powered HTML template, highlighting
    differences at both the node and inline text level.

    Attributes:
        manager: The comparator manager providing the comparison data.
    """

    def __init__(
        self,
        ctx: "QtContext",
        manager: ComparatorManager,
        parent=None,
    ) -> None:
        """Initialize the comparator web view.

        Args:
            ctx: The Qt context for translations and icons.
            manager: The comparator manager with sources and comparison data.
            parent: Optional parent widget.
        """
        # Store manager reference.
        self.manager = manager

        # Ensure comparison data is ready.
        if not self.manager.data:
            self.manager.get_compare_data()
        self.manager.compare()

        # Resolve template path.
        this_dir = os.path.dirname(__file__)
        template_path = os.path.normpath(
            os.path.join(this_dir, "webview.html.j2")
        )

        # Initialize base TemplViewer with the compare template and context.
        super().__init__(
            ctx=ctx,
            var_bag=VarBag(),
            parent=parent,
            extra_context=self._build_context(),
            template_src=template_path,
            prevent_render=False,
            var_model=None,
            highlight_code=False,
        )

    # --- Rendering ---------------------------------------------------------
    def refresh(self) -> None:
        """Refresh the comparison data and re-render the view."""
        try:
            # Re-run comparison.
            if not self.manager.data:
                self.manager.get_compare_data()
            self.manager.compare()

            # Re-render with updated context.
            self.render_template(**self._build_context())
        except Exception:
            logger.exception("Failed refreshing comparator web view")

    def _build_context(self) -> Dict[str, Any]:
        """Build the template context for the compare view.

        Returns:
            A dictionary with source names and the structured comparison tree.
        """
        # Get source names.
        source_names: List[str] = []
        for adapter in self.manager.sources:
            name = getattr(adapter, "name", adapter.__class__.__name__)
            source_names.append(name)

        # Convert the tree structure to template-friendly format.
        tree_data = self._convert_tree_to_dict(self.manager.root)

        return {
            "source_names": source_names,
            "num_sources": len(source_names),
            "tree": tree_data,
        }

    def _convert_tree_to_dict(
        self, node: ParentNode, depth: int = 0
    ) -> Dict[str, Any]:
        """Convert a tree node to a dictionary for template rendering.

        Args:
            node: The parent node to convert.
            depth: Current depth in the tree (for indentation).

        Returns:
            A dictionary with node information and children.
        """
        children_data: List[Dict[str, Any]] = []

        for child in node.children:
            if isinstance(child, LeafNode):
                # Leaf node: extract values for each source.
                cell_data = self._extract_leaf_values(child)
                children_data.append(
                    {
                        "type": "leaf",
                        "key": child.key,
                        "label": child.label,
                        "cells": cell_data,
                        "status": self._get_leaf_status(child),
                    }
                )
            elif isinstance(child, ParentNode):
                # Parent node: recurse.
                children_data.append(
                    {
                        "type": "parent",
                        "key": child.key,
                        "label": child.label,
                        "children": self._convert_tree_to_dict(
                            child, depth + 1
                        )["children"],
                        "mismatch_count": child.mismatch_count,
                    }
                )

        return {
            "label": node.label if depth == 0 else "",
            "children": children_data,
        }

    def _extract_leaf_values(self, node: LeafNode) -> List[Dict[str, Any]]:
        """Extract and format values from a leaf node for each source.

        Args:
            node: The leaf node to extract values from.

        Returns:
            A list of dictionaries, one per source, with formatted HTML.
        """
        result: List[Dict[str, Any]] = []

        # Build a map from source to value.
        source_to_value: Dict[Any, Value] = {}
        for value in node.values:
            source_to_value[value.source] = value

        # Create entries for each source in order.
        for adapter in self.manager.sources:
            value_obj = source_to_value.get(adapter)
            if value_obj is None or not value_obj.exists:
                result.append(
                    {
                        "exists": False,
                        "value": None,
                        "html": "",
                    }
                )
            else:
                val_str = self._to_str(value_obj.value)
                # Use LeafNode's HTML escape method.
                result.append(
                    {
                        "exists": True,
                        "value": value_obj.value,
                        "html": LeafNode._html_escape(val_str),
                    }
                )

        # If we have multiple sources with values, compute inline diffs.
        # Compare each source to the first source (base).
        if len(result) >= 2:
            base_idx = 0
            base_val = result[base_idx]["value"]
            base_str = self._to_str(base_val) if base_val is not None else ""
            base_html_computed = False

            for idx in range(1, len(result)):
                if not result[idx]["exists"]:
                    continue
                crt_val = result[idx]["value"]
                crt_str = self._to_str(crt_val) if crt_val is not None else ""

                if base_str != crt_str:
                    # Compute inline diff using LeafNode method.
                    # Use a temporary leaf node instance for html_diff.
                    temp_leaf = LeafNode(manager=self.manager, key="", label="")
                    left_html, right_html = temp_leaf.html_diff(
                        base_str, crt_str
                    )
                    # Only update base HTML once (on first difference).
                    if not base_html_computed:
                        result[base_idx]["html"] = left_html
                        base_html_computed = True
                    result[idx]["html"] = right_html

        return result

    def _get_leaf_status(self, node: LeafNode) -> str:
        """Determine the status of a leaf node for styling.

        Args:
            node: The leaf node to check.

        Returns:
            Status string: 'same', 'modified', 'left_only', or 'right_only'.
        """
        if node.are_equal:
            return "same"

        # Check which sources have values.
        has_values = [v.exists for v in node.values]
        if not any(has_values):
            return "same"

        # If only first source has value.
        if has_values[0] and not any(has_values[1:]):
            return "left_only"

        # If only other sources have values (but not the first).
        if not has_values[0] and any(has_values[1:]):
            # If only one other source has value, it's "right_only".
            if sum(has_values[1:]) == 1:
                return "right_only"
            # Multiple sources but not the first.
            return "modified"

        # Otherwise, modified (multiple sources with different values).
        return "modified"

    def _to_str(self, v: Any) -> str:
        """Convert a value to string, handling None safely.

        Args:
            v: The value to convert.

        Returns:
            String representation of the value.
        """
        try:
            if v is None:
                return ""
            return str(v)
        except Exception:
            return ""
