"""Record adapter that delegates merge editor creation to fields by key.

When field_map is provided, create_merge_editor looks up the leaf key and
calls field.cmp_create_manual_editor so relation fields can provide SiSe/
MuSe widgets.
"""

from typing import TYPE_CHECKING, Any, Dict, Optional

from exdrf_qt.comparator.widgets.record_to_node_adapter import (
    LeafDataCallable,
    RecordToNodeAdapter,
)

if TYPE_CHECKING:
    from exdrf_qt.models.field import QtField


class FieldAwareRecordAdapter(RecordToNodeAdapter):
    """Record adapter that delegates merge editor creation to fields by key.

    When field_map is provided, create_merge_editor looks up the leaf key and
    calls field.cmp_create_manual_editor so relation fields can provide SiSe/
    MuSe widgets.

    Attributes:
        _field_map: Mapping of leaf key -> field instance for
            cmp_create_manual_editor delegation.
    """

    _field_map: Dict[str, "QtField"]

    def __init__(
        self,
        name: str,
        get_leaf_data: "LeafDataCallable",
        field_map: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Build an adapter that can delegate to fields for merge editors.

        Args:
            name: Display name for this source.
            get_leaf_data: Callable returning (key, label, value) list.
            field_map: Optional mapping leaf key -> field instance for
                cmp_create_manual_editor delegation.
        """
        super().__init__(name=name, get_leaf_data=get_leaf_data)
        self._field_map = field_map or {}

    def create_merge_editor(
        self,
        parent: Any,
        context: Any,
        state: Any,
        current_value: Any,
    ) -> Optional[Any]:
        """Delegate to field.cmp_create_manual_editor when key is in field_map.

        Args:
            parent: The parent widget.
            context: The context.
            state: The state.
            current_value: The current value.
        """
        field = self._field_map.get(context.leaf.key)
        if field is None or not hasattr(field, "cmp_create_manual_editor"):
            return None
        return field.cmp_create_manual_editor(
            parent, context, state, current_value
        )
