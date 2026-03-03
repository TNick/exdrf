"""Base widget and adapter for record compare/merge (cmp) widgets.

Provides RecordComparatorBase (tabbed tree + webview + optional result preview)
and RecordToNodeAdapter to turn a single record's (key, label, value) list
into a comparator tree source.

Re-exports from dedicated modules for backward compatibility.
"""

from exdrf_qt.comparator.widgets.cmp_result_preview_pane import (
    CmpResultPreviewPane,
)
from exdrf_qt.comparator.widgets.field_aware_record_adapter import (
    FieldAwareRecordAdapter,
)
from exdrf_qt.comparator.widgets.record_comparator_base import (
    RecordComparatorBase,
)
from exdrf_qt.comparator.widgets.record_to_node_adapter import (
    LeafDataCallable,
    LeafDataItem,
    RecordToNodeAdapter,
)

__all__ = [
    "CmpResultPreviewPane",
    "FieldAwareRecordAdapter",
    "LeafDataCallable",
    "LeafDataItem",
    "RecordComparatorBase",
    "RecordToNodeAdapter",
]
