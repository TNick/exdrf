import logging
from collections import namedtuple
from functools import cached_property
from typing import TYPE_CHECKING, Any, Dict, List, Sequence, Tuple, Type

from attrs import define, field
from exdrf.constants import RecIdType
from exdrf.validator import ValidationResult
from PyQt5.QtCore import QModelIndex, Qt
from PyQt5.QtWidgets import QAbstractItemView
from sqlalchemy import delete, select

from exdrf_qt.field_ed.fed_related.base_adapter import BaseAdapter

if TYPE_CHECKING:
    from exdrf_qt.models.model import QtModel
    from exdrf_qt.models.record import QtRecord

logger = logging.getLogger(__name__)


@define
class BridgeAdapter(BaseAdapter):
    """Adapter for jump tables that contain the primary keys of the two related
    models, along with some other fields that are used to describe the
    relationship.

    Attributes:
        list_pk: The name of the field in the bridge model that contains
            the ID of the record in the list model.
        edit_pk: The name of the field in the bridge model that contains
            the ID of the record in the edit model.
        list_rel: The name of the field in the bridge model that
            represents the relationship to the list model.
        edit_rel: The name of the field in the bridge model that
            represents the relationship to the edit model.
        other_pk: The names of the other primary keys of the bridge model.
    """

    list_pk: str = field(repr=False, kw_only=True)
    edit_pk: str = field(repr=False, kw_only=True)
    list_rel: str = field(repr=False, kw_only=True)
    edit_rel: str = field(repr=False, kw_only=True)
    other_pk: list[str] = field(repr=False, kw_only=True)
    other_fields: list[str] = field(repr=False, kw_only=True)

    def adjust_model(self, model: "QtModel") -> None:
        model.column_fields = [
            f.name
            for f in model.column_fields
            if f.name not in (self.edit_pk, self.edit_rel)
        ]
        model.allow_top_cache_edit = True

    def started(self) -> None:
        self.core.dst_model.dataChanged.connect(self._on_dst_data_changed)
        # self.core.dst_list.setEditTriggers(
        #     QAbstractItemView.EditTrigger.AllEditTriggers
        # )
        self.core.dst_list.setSelectionMode(
            QAbstractItemView.SelectionMode.MultiSelection
        )

    def _on_dst_data_changed(
        self,
        top: "QModelIndex",
        bottom: "QModelIndex",
        roles: List[Qt.ItemDataRole],
    ) -> None:
        """Handle the data being changed in the destination model."""
        if Qt.ItemDataRole.EditRole in roles:
            self.core.controlChanged.emit()

    @cached_property
    def mock_db_class(self) -> Type[Any]:
        fields = []
        if self.list_pk:
            fields.append(self.list_pk)
        if self.edit_pk:
            fields.append(self.edit_pk)
        if self.list_rel:
            fields.append(self.list_rel)
        if self.edit_rel:
            fields.append(self.edit_rel)
        fields.extend(self.other_pk)
        fields.extend(self.other_fields)
        return namedtuple("MockDbClass", fields)

    def new_mock_from_list_item(
        self, list_item: Any, list_item_id: RecIdType, **kwargs
    ) -> Any:
        mock_db_class = self.mock_db_class

        values = []
        if self.list_pk:
            values.append(list_item_id)
        if self.edit_pk:
            values.append(None)
        if self.list_rel:
            values.append(list_item)
        if self.edit_rel:
            values.append(None)
        for x in self.other_pk:
            values.append(kwargs.get(x, None))
        for x in self.other_fields:
            values.append(kwargs.get(x, None))
        return mock_db_class(*values)

    def add_db_ids(
        self,
        db_id_list: List[RecIdType],
        extra: Dict[RecIdType, Dict[str, Any]] = {},
    ):
        # Get the destination model.
        list_model: "QtModel" = self.core.src_model
        bridge_model: "QtModel" = self.core.dst_model
        list_db_model = list_model.db_model
        other_pk_keys = []

        with self.ctx.same_session() as session:
            # Read these records from the database.
            dst_records = session.scalars(
                select(list_db_model).where(
                    list_model.get_id_filter(db_id_list)
                )
            )
            # And create a ID record map.
            result_map: Dict[RecIdType, Any] = {
                list_model.get_db_item_id(r): r for r in dst_records
            }

            # Check to see if we were able to find all the records in the
            # database. Trim those that were not found.
            ordered_records = []
            for db_id in db_id_list:
                if db_id not in result_map:
                    logger.error(
                        "Record %s not found in the database",
                        db_id,
                    )
                    continue
                ordered_records.append(result_map[db_id])
            if not ordered_records:
                return

            # Create model records out of each database record.
            new_items = []
            for db_rec in ordered_records:
                extra_data = extra.get(db_rec.id, {})
                # We use these to create the database key.
                other_pk_keys = [extra_data.get(x, None) for x in self.other_pk]
                db_id = self.create_record_id(db_rec.id, other_pk_keys)
                mock = self.new_mock_from_list_item(
                    db_rec, db_rec.id, **extra_data
                )
                m_record = bridge_model.db_item_to_record(mock)
                m_record.loaded = True
                new_items.append(m_record)

            # Add these values to the top.
            bridge_model.insert_new_records(new_items)

        # Update the field value.
        self.core.field_value = id(other_pk_keys)

    def add_records(self, records: Sequence["QtRecord"]) -> None:

        # Get the list of IDs to add.
        incoming = [r.db_id for r in records if r.db_id is not None]
        self.add_db_ids(incoming)

    def remove_records(self, records: Sequence[Tuple["QtRecord", int]]) -> None:
        # Get the destination model.
        model: "QtModel" = self.core.dst_model

        remove_from_top = set()

        for record, row in records:
            if row < len(model.top_cache):
                remove_from_top.add(row)
            else:
                record.soft_del = True
                model.dataChanged.emit(
                    model.index(row, 0),
                    model.index(row, len(model.column_fields) - 1),
                )

        if remove_from_top:
            model.set_top_records(
                [
                    record
                    for row, record in enumerate(model.top_cache)
                    if row not in remove_from_top
                ]
            )

        # Update the field value.
        self.core.field_value = id(remove_from_top)

    def change_field_value(self, new_value) -> None:
        print(new_value)

    def load_value_from(self, record: Any):
        model: "QtModel" = self.core.dst_model

        # Get the ID of the record being loaded.
        db_id = self.core.form.get_id_of_record(record)

        # Remove any top level (dynamically added) record.
        model.top_cache.clear()

        # Set the filter.
        model.base_selection = (
            select(model.db_model)
            .join(getattr(model.db_model, self.edit_rel))
            .where(getattr(model.db_model, self.edit_pk) == db_id)
        )
        model.reset_model()

    def save_value_to(self, record: Any):
        # Get the destination model.
        model: "QtModel" = self.core.dst_model

        with self.core.ctx.same_session() as session:
            if record.id is not None:
                # Remove previous records for this record.
                stm = delete(model.db_model).where(
                    getattr(model.db_model, self.edit_pk) == record.id
                )
                session.execute(stm)

            # Add new records for this record.
            for m_record, row in model.iter_records(
                include_top=True,
                include_not_loaded=False,
                include_error=False,
                include_no_data=False,
            ):
                if m_record.soft_del:
                    continue
                db_rec = model.record_to_data(m_record, session)
                setattr(db_rec, self.edit_rel, record)
                session.add(db_rec)
            session.commit()

    def create_record_id(
        self, list_id: RecIdType, other_pk: list[Any]
    ) -> RecIdType:
        return (list_id, *other_pk)

    def validate_control(self) -> "ValidationResult":
        if not self.core.dst_model.is_fully_loaded:
            self.core.dst_model.ensure_fully_loaded()
            return ValidationResult(
                reason="REQUIRED",
                error=self.core.t(
                    "cmn.err.model_not_fully_loaded",
                    "The model is not fully loaded.",
                ),
            )

        c_fields = [f.name for f in self.core.dst_model.column_fields]
        list_rel_index = c_fields.index(self.list_rel)
        other_pk_index = [c_fields.index(p) for p in self.other_pk]

        names = [*self.other_pk, self.list_rel]

        def check_row_data(the_record):
            row = the_record.get_row_data(Qt.ItemDataRole.EditRole)
            pk_list = [row[i] for i in other_pk_index]
            pk_list.append(row[list_rel_index])
            if any(pk is None for pk in pk_list):
                pairs = zip(names, pk_list)
                missing = [f for f, v in pairs if v is None]
                return ValidationResult(
                    reason="REQUIRED",
                    error=self.core.t(
                        "cmn.err.missing_field_value",
                        "Missing value for {field}.",
                        field=missing,
                    ),
                )

        # Make sure that all required fields have a value.
        for top_r in self.core.dst_model.top_cache:
            result = check_row_data(top_r)
            if result is not None:
                return result

        for reg_r in self.core.dst_model.cache:
            result = check_row_data(reg_r)
            if result is not None:
                return result

        return ValidationResult(value=self.core._field_value or [])
