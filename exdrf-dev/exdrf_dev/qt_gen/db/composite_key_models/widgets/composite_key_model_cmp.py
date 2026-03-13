# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> c/m/w/cmp.py.j2
# Don't change it manually.

import logging
from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Type

from exdrf.constants import RecIdType
from exdrf_qt.controls import (
    FieldAwareRecordAdapter,
    RecordComparatorBase,
    RecordToNodeAdapter,
)
from exdrf_qt.plugins import exdrf_qt_pm
from exdrf_qt.utils.plugins import safe_hook_call
from sqlalchemy import select

# exdrf-keep-start other_imports -----------------------------------------------

# exdrf-keep-end other_imports -------------------------------------------------

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from exdrf_qt.controls.templ_viewer.templ_viewer import RecordTemplViewer
    from sqlalchemy.orm import Session  # noqa: F401

    from exdrf_dev.db.api import (
        CompositeKeyModel as CompositeKeyModel,
    )  # noqa: F401

logger = logging.getLogger(__name__)

# Leaf keys (key, label) for comparator columns; values come from each record.
_CMP_LEAF_KEYS: List[Tuple[str, str]] = [
    ("description", "Description"),
    ("some_binary", "Some binary"),
    ("some_date", "Some date"),
    ("some_enum", "Some enum"),
    ("some_float", "Some float"),
    ("some_json", "Some json"),
    ("some_time", "Some time"),
    ("related_items", "Related items"),
    ("key_part1", "Key part1"),
    ("key_part2", "Key part2"),
]

# exdrf-keep-start other_globals -----------------------------------------------

# exdrf-keep-end other_globals -------------------------------------------------


class QtCompositeKeyModelCmp(RecordComparatorBase):
    """Compare/merge widget for CompositeKeyModel records.

    Supports compare-only or merge mode (set at construction). Use record_ids
    to load records and build the comparison.
    """

    # exdrf-keep-start other_attributes ----------------------------------------

    # exdrf-keep-end other_attributes ------------------------------------------

    def __init__(
        self, ctx: "QtContext", parent: Optional[Any] = None, **kwargs
    ):
        """Initialize the compare/merge widget.

        Args:
            ctx: Qt context for i18n and DB session.
            parent: Optional parent widget.
            **kwargs: record_ids: optional list of record IDs to compare;
                merge_enabled: optional bool (default False).
        """
        from exdrf_dev.db.api import CompositeKeyModel as DbCompositeKeyModel

        record_ids = kwargs.pop("record_ids", None)
        merge_enabled = kwargs.pop("merge_enabled", False)

        super().__init__(
            ctx=ctx,
            parent=parent,
            merge_enabled=merge_enabled,
            record_ids=record_ids,
            **kwargs,
        )

        if not self.windowTitle():
            self.setWindowTitle(
                self.t(
                    "composite_key_model.cmp.title",
                    "Composite key model compare",
                ),
            )

        adapters: List[RecordToNodeAdapter] = []
        if record_ids:
            from exdrf_dev.qt_gen.db.composite_key_models.models.composite_key_model_ful import (
                QtCompositeKeyModelFuMo,
            )

            ful = QtCompositeKeyModelFuMo(ctx=ctx, prevent_total_count=True)
            field_map = {f.name: f for f in ful.fields}

            with self.ctx.same_session() as session:
                for i, rec_id in enumerate(record_ids):
                    rec = self._load_record(
                        session, DbCompositeKeyModel, rec_id
                    )
                    if rec is not None:
                        name = self.t(
                            "composite_key_model.cmp.record_label",
                            "Record {n}",
                            n=i + 1,
                        )
                        adapters.append(
                            FieldAwareRecordAdapter(
                                name=name,
                                get_leaf_data=lambda r=rec: [
                                    (k, l, getattr(r, k, None))
                                    for k, l in _CMP_LEAF_KEYS
                                ],
                                field_map=field_map,
                            )
                        )
            self.set_sources(adapters)

        # exdrf-keep-start extra_cmp_init --------------------------------------

        # exdrf-keep-end extra_cmp_init ----------------------------------------

        safe_hook_call(
            exdrf_qt_pm.hook.composite_key_model_cmp_created,
            widget=self,
        )

    def _get_cmp_load_options(self, db_model: type) -> list:
        """Return SQLAlchemy load options for eager-loading relationships.

        Override in subclasses or via other_attributes to avoid
        DetachedInstanceError when leaf keys access relationships (e.g. hybrid
        properties). Default returns no options.
        """
        return []

    def _load_record(
        self,
        session: "Session",
        db_model: type,
        record_id: RecIdType,
    ) -> Optional["CompositeKeyModel"]:
        """Load one record by primary key (with optional eager-load options)."""

        stmt = select(db_model).where(
            db_model.key_part1 == record_id[0],  # type: ignore
            db_model.key_part2 == record_id[1],  # type: ignore
        )

        load_opts = self._get_cmp_load_options(db_model)
        if load_opts:
            stmt = stmt.options(*load_opts)
        return session.scalar(stmt)

    def get_viewer_class(self) -> Type["RecordTemplViewer"]:
        from .composite_key_model_tv import QtCompositeKeyModelTv

        return QtCompositeKeyModelTv
