from exdrf_qt.controls.base_editor import ExdrfEditor  # noqa: F401
from exdrf_qt.controls.table_list import ListDb  # noqa: F401
from exdrf_qt.controls.table_viewer import TableViewer  # noqa: F401
from exdrf_qt.controls.transfer import TransferWidget  # noqa: F401


def __getattr__(name: str):
    """Lazy-load record_cmp_base to avoid pulling PyQt6-WebEngine for db2qt etc."""
    _names = (
        "CmpResultPreviewPane",
        "FieldAwareRecordAdapter",
        "RecordComparatorBase",
        "RecordToNodeAdapter",
    )
    if name in _names:
        from exdrf_qt.controls.record_cmp_base import (
            CmpResultPreviewPane,
            FieldAwareRecordAdapter,
            RecordComparatorBase,
            RecordToNodeAdapter,
        )

        return {
            "CmpResultPreviewPane": CmpResultPreviewPane,
            "FieldAwareRecordAdapter": FieldAwareRecordAdapter,
            "RecordComparatorBase": RecordComparatorBase,
            "RecordToNodeAdapter": RecordToNodeAdapter,
        }[name]
    raise AttributeError("module %r has no attribute %r" % (__name__, name))
