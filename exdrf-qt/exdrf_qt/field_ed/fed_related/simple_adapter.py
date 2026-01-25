import logging
from typing import TYPE_CHECKING, Any, Dict, Sequence, Tuple

from attrs import define, field
from sqlalchemy import select
from sqlalchemy.orm import load_only
from sqlalchemy.orm.collections import InstrumentedList, InstrumentedSet

from exdrf_qt.field_ed.fed_related.base_adapter import BaseAdapter

if TYPE_CHECKING:
    from exdrf.constants import RecIdType

    from exdrf_qt.models.model import QtModel
    from exdrf_qt.models.record import QtRecord

logger = logging.getLogger(__name__)


@define
class SimpleAdapter(BaseAdapter):
    """Adapter for simple jump tables that only contain the primary
    keys of the two related models.

    In this case we share the loaded records from source model when adding
    records.
    """

    db_map: Dict["RecIdType", Any] = field(factory=dict, repr=False, init=False)

    def add_records(self, records: Sequence["QtRecord"]) -> None:
        # Get the destination model.
        model: "QtModel" = self.core.dst_model

        # Insert the records as they are in the top cache, but only if they
        # are not already in the model.
        to_add = []
        for record in records:
            db_id = record.db_id
            if db_id is None:
                logger.error("Record %s has no ID", record)
                continue
            sts = self.db_map.get(db_id, None)
            if sts is None:
                to_add.append(record)
            elif sts == "deleted":
                # This is a record that was loaded from the database and we can
                # simply restore it.
                self.db_map[db_id] = "keep"
                record.soft_del = False
                row = model._db_to_row.get(db_id, None)
                if row is None:
                    logger.error("Record %s not found in db_to_row", db_id)
                    continue
                model.dataChanged.emit(
                    model.index(row, 0),
                    model.index(row, len(model.column_fields) - 1),
                )
            else:
                logger.error("Record %s already in db_map", db_id)

        # New records get added to the top cache.
        if to_add:
            self.db_map.update({r.db_id: "added" for r in to_add})
            model.insert_new_records(to_add)

        # Update the field value.
        self.core.field_value = list(self.db_map.keys())

    def remove_records(self, records: Sequence[Tuple["QtRecord", int]]) -> None:
        # Get the destination model.
        model: "QtModel" = self.core.dst_model

        # Get the list of records to remove indexed by their ID.
        remove_list = {r[0].db_id: r for r in records if r[0].db_id is not None}

        remove_from_top = set()
        for db_id, (record, row) in remove_list.items():
            sts = self.db_map.get(db_id, None)
            if sts is None:
                logger.error("Record %s not found in db_map", db_id)
                continue

            if sts == "added":
                # This is a record that was added in this session and we can
                # simply remove it from the model.
                remove_from_top.add(db_id)
                del self.db_map[db_id]
            elif sts == "keep":
                # This is a record loaded from the database.
                # We need to mark it as deleted.
                self.db_map[db_id] = "deleted"
                record.soft_del = True
                model.dataChanged.emit(
                    model.index(row, 0),
                    model.index(row, len(model.column_fields) - 1),
                )
            elif sts == "deleted":
                # Nothing to do here.
                pass
            else:
                logger.error("Unknown status %s for record %s", sts, db_id)

        if remove_from_top:
            model.set_top_records(
                [r for r in model.top_cache if r.db_id not in remove_from_top]
            )

        # Update the field value.
        self.core.field_value = list(self.db_map.keys())

    def load_value_from(self, record: Any):
        # Get the destination model.
        model: "QtModel" = self.core.dst_model

        # Get the ID of the record being loaded.
        db_id = self.core.form.get_id_of_record(record)

        # Remove any top level (dynamically added) record.
        model.top_cache.clear()

        # Set the filter.
        model.base_selection = (
            select(model.db_model)
            .join(getattr(record.__class__, self.core._name))
            .where(getattr(record.__class__, "id") == db_id)
        )
        model.reset_model()

        # Read the IDs from the database.
        with self.core.ctx.same_session() as session:
            self.db_map = {
                db_id: "keep"
                for db_id in session.scalars(
                    select(getattr(model.db_model, "id"))
                    .join(getattr(record.__class__, self.core._name))
                    .where(getattr(record.__class__, "id") == db_id)
                )
            }

    def save_value_to(self, record: Any):
        # Get the destination model.
        model: "QtModel" = self.core.dst_model

        # Get the records that should be part of the relation.
        db_ids = [
            db_id
            for db_id, sts in self.db_map.items()
            if sts in ("keep", "added")
        ]

        with self.core.ctx.same_session() as session:
            stm = (
                select(model.db_model)
                .where(getattr(model.db_model, "id").in_(db_ids))
                .options(load_only(getattr(model.db_model, "id")))
            )
            records = session.scalars(stm).all()
            if len(records) != len(db_ids):
                logger.error(
                    "Expected %d records, got %d", len(db_ids), len(records)
                )

            crt_rec = getattr(record, self.core._name)
            if isinstance(crt_rec, InstrumentedSet):
                records = set(records)
            elif isinstance(crt_rec, InstrumentedList):
                records = list(records)
            else:
                raise ValueError(
                    "Expected a set or list, got %s",
                    type(crt_rec).__name__,
                )

            setattr(record, self.core._name, records)
