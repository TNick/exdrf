import logging
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Set,
    Type,
    TypeVar,
)
from uuid import uuid4

from exdrf.validator import ValidationResult
from PyQt5.QtCore import QModelIndex, Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import select

from exdrf_qt.controls.table_list import TreeViewDb
from exdrf_qt.field_ed.base import DrfFieldEd
from exdrf_qt.models.model import QtModel
from exdrf_qt.models.record import QtRecord

if TYPE_CHECKING:
    from exdrf.constants import RecIdType
    from sqlalchemy.orm import Session

    from exdrf_qt.context import QtContext

DBM = TypeVar("DBM")
logger = logging.getLogger(__name__)


class DrfRelated(QWidget, Generic[DBM], DrfFieldEd):
    """A widget that allows the user to manage relationships where multiple
    records are associated with the current record.

    The widget contains two lists:
    - to the right is the list of available records that are not associated
      with the current record;
    - to the left is the list of records that are associated with the
      current record.

    The middle part contains two buttons:
    - "Add" button to associate a record with the current record;
    - "Remove" button to disassociate a record from the current record.

    The resources can be in a many-to-one relationship, in which case
    the foreign resource contains the current record's ID or in a many-to-many
    relationship, in which case there is a junction resource that contains the
    current record's ID and the foreign record's ID, along with
    some other fields that are used to describe the relationship.

    Attributes:
        implicit_set: The set of names that indicate the fields which map from
            the join table to the model in the editor. The foreign key
            is always present and should have the _id suffix. If the
            join model includes a relationship, its name will also
            be present. The length of this list is always either 1 or 2.
    """

    implicit_set: Set[str]
    inserted: Dict[str, "QtRecord"]
    removed: Dict["RecIdType", "QtRecord"]
    final_db_model: Type[DBM]
    mirror_field: str
    is_simple: bool
    _implicit_values: List[Any]
    src_label_fun: Callable[[DBM], str]

    def __init__(
        self,
        ctx: "QtContext",
        dst_model: Type[QtModel[DBM]],
        src_model: Type[QtModel[DBM]],
        dst_db_model: Type[DBM],
        src_db_model: Type[DBM],
        final_db_model: Type[DBM],
        implicit_set: List[str],
        exclude_set: List[str],
        mirror_field: str,
        src_label_fun: Callable[[DBM], str],
        is_simple: bool = False,
        **kwargs,
    ):
        self.ctx = ctx
        self.inserted = {}
        self._implicit_values = []
        self.final_db_model = final_db_model
        self.is_simple = is_simple
        self.mirror_field = mirror_field
        self.src_label_fun = src_label_fun

        assert len(implicit_set) in [1, 2]
        self.implicit_set = set(implicit_set)

        # Initialize parent classes.
        QWidget.__init__(self, kwargs.pop("parent", None))
        DrfFieldEd.__init__(self, ctx=ctx, **kwargs)
        self._field_value = []
        self._nullable = False

        # Source model.
        self.src_model = src_model(ctx=ctx, db_model=src_db_model, parent=self)

        # Create the destination model.
        if is_simple:
            self.dst_model = src_model(
                ctx=ctx,
                db_model=src_db_model,
                parent=self,
                prevent_total_count=True,
                selection=select(src_db_model).where(
                    src_db_model.id.is_(None)  # type: ignore
                ),
            )

        else:
            self.dst_model = dst_model(
                ctx=ctx,
                db_model=dst_db_model,
                parent=self,
                prevent_total_count=True,
            )
            if implicit_set or exclude_set:
                self.dst_model.column_fields = [
                    f.name
                    for f in self.dst_model.fields
                    if f.name not in implicit_set and f.name not in exclude_set
                ]

        self.dst_model.recalculate_total_count()

        # Create the main layout.
        self.lay_main = QHBoxLayout()

        # Create the source list.
        self.src_list = TreeViewDb(parent=self, ctx=ctx)
        self.src_list.setModel(self.src_model)
        self.src_list.setSelectionMode(
            QAbstractItemView.SelectionMode.MultiSelection
        )
        self.lay_main.addWidget(self.src_list)

        # Create the middle buttons.
        self.create_middle_buttons()

        # Create the destination list.
        self.dst_list = TreeViewDb(parent=self, ctx=ctx)
        self.dst_list.setModel(self.dst_model)
        self.src_list.setSelectionMode(
            QAbstractItemView.SelectionMode.MultiSelection
        )
        self.lay_main.addWidget(self.dst_list)

        # Keep button states synced with list selection changes.
        self._init_selection_tracking()

        # Initialize button states based on initial selection.
        self._update_button_states()

    def create_middle_buttons(self) -> None:
        self.lay_btns = QVBoxLayout()
        self.lay_btns.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )
        self.btn_add = QPushButton(self.t("cmn.add-left", "Add 🡆"), parent=self)
        self.btn_add.setEnabled(False)
        self.lay_btns.addWidget(self.btn_add)
        self.btn_remove = QPushButton(
            self.t("cmn.remove-right", "🡄 Remove"), parent=self
        )
        self.btn_remove.setEnabled(False)
        self.lay_btns.addWidget(self.btn_remove)
        self.lay_btns.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )
        self.lay_main.addLayout(self.lay_btns)

        # Set the layout for the page.
        self.setLayout(self.lay_main)

        # Hook up menus and actions.
        self._init_menus_and_actions()

    def _init_menus_and_actions(self) -> None:
        """Initialize context menus and button actions for the lists."""

        # Buttons: perform the same operations as context menus.
        self.btn_add.clicked.connect(self._on_add_clicked)
        self.btn_remove.clicked.connect(self._on_remove_clicked)

    def _init_selection_tracking(self) -> None:
        """Track selection changes for button updates."""

        # Update Add button when the source selection changes.
        src_sm = self.src_list.selectionModel()
        if src_sm is not None:
            src_sm.selectionChanged.connect(self._on_selection_changed)

        # Update Remove button when the destination selection changes.
        dst_sm = self.dst_list.selectionModel()
        if dst_sm is not None:
            dst_sm.selectionChanged.connect(self._on_selection_changed)

    def _on_selection_changed(self, *args: Any) -> None:
        """Handle selection changes in either list."""
        self._update_button_states()

    def _on_add_clicked(self) -> None:
        """Handle the Add action (left -> right)."""

        # Collect the selected source records.
        src_sm = self.src_list.selectionModel()
        if src_sm is None:
            return
        selected_rows = [i.row() for i in src_sm.selectedRows()]
        if not selected_rows:
            return

        existing = set(self.field_value or [])
        new_value = list(self._field_value)
        new_items = []
        if self.is_simple:
            for idx in selected_rows:
                src_record = self.src_model.data_record(idx)
                if src_record is None or src_record.db_id is None:
                    continue
                if src_record.db_id in existing:
                    continue
                new_items.append(src_record)
                existing.add(src_record.db_id)
                new_value.append(src_record.db_id)
            if new_items:
                self.dst_model.insert_new_records(new_items)
                self._change_field_value(new_value)
        else:
            # Retrieve the IDs of the selected database records from the
            # left (source) model.
            db_ids = [
                self.src_model.data_record(idx).db_id  # type: ignore
                for idx in selected_rows
            ]
            with self.ctx.same_session() as session:
                # Read these records from the database.
                dst_records = session.scalars(
                    select(self.src_model.db_model).where(
                        self.src_model.get_id_filter(db_ids)
                    )
                )
                result_map: Dict[RecIdType, DBM] = {
                    self.src_model.get_db_item_id(r): r for r in dst_records
                }

                # Check to see if we were able to find all the records in the
                # database. Trim those that were not found.
                ordered_records = []
                for db_id in db_ids:
                    if db_id not in result_map:
                        logger.error(
                            "Record %s not found in the database",
                            db_id,
                        )
                        continue
                    ordered_records.append(result_map[db_id])
                if not ordered_records:
                    return

                # For each database record we create a new top-level record in
                # the right (mapping) list.
                c_fields = [f.name for f in self.dst_model.column_fields]
                mirror_index = c_fields.index(self.mirror_field)

                for db_rec in ordered_records:
                    tmp_id = str(uuid4().hex)
                    m_record = QtRecord(
                        model=self.dst_model,
                        db_id=tmp_id,
                        soft_del=False,
                    )
                    m_record.values[mirror_index] = {
                        Qt.ItemDataRole.DisplayRole: str(
                            self.src_label_fun(db_rec)
                        ),
                        Qt.ItemDataRole.EditRole: self.src_model.get_db_item_id(
                            db_rec
                        ),
                    }
                    m_record.loaded = True
                    new_items.append(m_record)
                    new_value.append(tmp_id)
                self.dst_model.insert_new_records(new_items)
                self._change_field_value(new_value)

        # Update the buttons after the model changes.
        self._update_button_states()

    def _on_remove_clicked(self) -> None:
        """Handle the Remove action (right -> left)."""

        # Collect the selected destination records.
        dst_sm = self.dst_list.selectionModel()
        if dst_sm is None:
            return
        selected_rows = dst_sm.selectedRows()
        if not selected_rows:
            return

        if self.is_simple:
            for idx in sorted([i.row() for i in selected_rows], reverse=True):
                if idx < len(self.dst_model.top_cache):
                    m_record = self.dst_model.top_cache[idx]
                    # This is a row that was added in this session.
                    self.dst_model.beginRemoveRows(QModelIndex(), idx, idx)
                    self.dst_model.top_cache.pop(idx)
                    self.dst_model.endRemoveRows()
                else:
                    m_record = self.dst_model.cache[
                        idx - len(self.dst_model.top_cache)
                    ]
                    self.dst_model.dataChanged.emit(
                        self.dst_model.index(idx, 0),
                        self.dst_model.index(
                            idx, len(self.dst_model.column_fields) - 1
                        ),
                    )
                    m_record.soft_del = True
                self._field_value.remove(m_record.db_id)
            self._change_field_value(list(self._field_value))
            return

        # Split temporary records from persisted ones.
        temp_rows = []
        field_value = [] if self.field_value is None else list(self.field_value)
        for idx in selected_rows:
            row = idx.row()
            dst_record = self.dst_model.data_record(row)
            if dst_record is None:
                logger.error(
                    "No destination record found for Remove action at row %d",
                    row,
                )
                continue

            record_key = str(dst_record.db_id)
            if record_key in self.inserted:
                temp_rows.append(row)
                self.inserted.pop(record_key, None)
                if dst_record.db_id in field_value:
                    field_value.remove(dst_record.db_id)
            else:
                self._mark_record_removed(dst_record, row)

        # Remove temporary records from the top cache.
        for row in sorted(temp_rows, reverse=True):
            self._remove_dst_top_cache_row(row)

        # Update the field value and button state.
        self._change_field_value(field_value)
        self._update_button_states()

    def _find_dst_fk_field(self) -> Optional[str]:
        """Locate the destination FK field pointing to source records."""

        # Choose a candidate FK field not part of the implicit set.
        candidates = [
            fld.name
            for fld in self.dst_model.fields
            if fld.name.endswith("_id") and fld.name not in self.implicit_set
        ]
        if not candidates:
            return None
        if len(candidates) > 1:
            logger.error(
                "Multiple FK candidates for dst model: %s",
                candidates,
            )
        return candidates[0]

    def _remove_dst_top_cache_row(self, row: int) -> None:
        """Remove a row from the destination model top cache."""

        # Guard against invalid or non-top-cache rows.
        if row < 0 or row >= len(self.dst_model.top_cache):
            logger.error(
                "Invalid row %d for Remove action",
                row,
            )
            return

        parent_idx = QModelIndex()
        self.dst_model.rowsAboutToBeRemoved.emit(parent_idx, row, row)
        self.dst_model.top_cache.pop(row)
        self.dst_model.rowsRemoved.emit(parent_idx, row, row)
        self.dst_model.totalCountChanged.emit(self.dst_model.total_count)

    def _mark_record_removed(self, record: "QtRecord", row: int) -> None:
        """Mark an existing record as removed for later edits."""

        record.soft_del = True

        # Refresh the row display.
        if len(self.dst_model.column_fields) > 0:
            left = self.dst_model.index(row, 0)
            right = self.dst_model.index(
                row, len(self.dst_model.column_fields) - 1
            )
            self.dst_model.dataChanged.emit(
                left,
                right,
                [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole],
            )

    def _update_button_states(self) -> None:
        """Update the enabled state of add/remove buttons based on selection."""
        # Check if left list has selection.
        src_sm = self.src_list.selectionModel()
        src_has_selection = (
            src_sm is not None
            and src_sm.hasSelection()
            and len(src_sm.selectedRows()) > 0
        )
        self.btn_add.setEnabled(src_has_selection)

        # Check if right list has selection.
        dst_sm = self.dst_list.selectionModel()
        dst_has_selection = (
            dst_sm is not None
            and dst_sm.hasSelection()
            and len(dst_sm.selectedRows()) > 0
        )
        self.btn_remove.setEnabled(dst_has_selection)

    def change_field_value(self, new_value: Any) -> None:
        """Change the field value."""
        if self.is_simple:
            new_value = new_value or []
        else:
            keys = [f for f in self.implicit_set if f.endswith("_id")]
            if not new_value:
                self.dst_model._fixed_filters = [  # type: ignore
                    "AND",
                    [{"fld": f, "op": "eq", "vl": None} for f in keys],
                ]
                new_value = []
            elif len(keys) == len(new_value):
                self.dst_model._fixed_filters = [  # type: ignore
                    "AND",
                    [
                        {"fld": f, "op": "eq", "vl": v}
                        for f, v in zip(keys, new_value)
                    ],
                ]
            else:
                raise ValueError(
                    "Expected %d values for %s, got %d",
                    len(keys),
                    keys,
                    len(new_value),
                )
            self._implicit_values = list(new_value or [])
        self._change_field_value(new_value)
        self.dst_model.reset_model()

    def constraints_changed(self, concept_key: str, new_value: Any) -> None:
        """React to the constraints being changed.

        Args:
            concept_key: The key of the concept that has changed.
            new_value: The new value of the concept.
        """
        # from exdrf.filter import validate_filter

        # from exdrf_qt.models.selector import Selector

        try:
            pass
            # if self._qt_model is None:
            #     logger.error("No model set")
            #     return

            # self._qt_model.constraints_changed(concept_key, new_value)
            # if self.is_empty:
            #     logger.log(1, "No field value set, nothing to check")
            #     return

            # TODO: Implement the logic
        except Exception as e:
            logger.error(
                "Error in constraints_changed for concept %s: %s",
                concept_key,
                e,
                exc_info=True,
            )

    def get_depends_on(self, default: Optional[List[str]] = None) -> List[str]:
        """Get the depends on for the field."""
        prop_deps = self.property("depends_on")
        if prop_deps is not None:
            result = []
            for part in prop_deps.split(","):
                if not part.strip():
                    continue
                concept, target = part.strip().split(":", maxsplit=1)
                result.append((concept.strip(), target.strip()))
            if result:
                return result
        return default or []

    def integrate_concepts(self, depends_on: List[str]):
        """Helper for set_form that allows you to declare in one go
        both the concept we provide and the ones that we depend on.
        """
        if not self.form:
            logger.error("Form is not set for %s", self.__class__.__name__)
            return

        for concept in self.get_depends_on(depends_on):
            self.form.constraints.register_subscriber(
                concept=concept,
                subscriber=self,
            )

    def validate_control(self) -> "ValidationResult":
        if not self.dst_model.is_fully_loaded:
            # Get an updated total count.
            self.dst_model.recalculate_total_count()

            # Request all items from the model.
            if self.dst_model.is_fully_loaded:
                self.dst_model.ensure_fully_loaded()

                return ValidationResult(
                    reason="NOT_INITIALIZED",
                    error=self.t(
                        "cmn.err.model_not_initialized",
                        "The model is not fully initialized.",
                    ),
                )
        return ValidationResult(value=self._field_value or [])

    def get_db_records(
        self, session: "Session", include_top: bool
    ) -> List[DBM]:

        # Only keep records that were not deleted by the user from previous
        # set.
        to_request = {}
        offset = 0
        if include_top:
            offset = len(self.dst_model.top_cache)
            for row, m_record in enumerate(self.dst_model.top_cache):
                if not m_record.soft_del:
                    to_request[m_record.db_id] = row
        for row, m_record in self.dst_model.cache.iter_existing():
            if not m_record.soft_del:
                to_request[m_record.db_id] = row + offset

        if to_request:
            found: List[Optional[DBM]] = [None for _ in range(len(to_request))]

            for db_record in session.scalars(
                select(self.dst_model.db_model).where(
                    self.dst_model.get_id_filter(list(to_request.keys()))
                )
            ):
                db_id = self.dst_model.get_db_item_id(db_record)
                row = to_request[db_id]
                found[row] = db_record
                to_request.pop(db_id, None)

            if to_request:
                logger.error(
                    "Some records were not found in the database: %s",
                    to_request.keys(),
                )
        else:
            return []

        return [f for f in found if f is not None]

    def save_value_to(self, record: Any):
        # Validate that the field name is set.
        if not self._name:
            raise ValueError("Field name is not set.")

        # At this point the model must be initialized and fully loaded.
        if self.dst_model.partially_initialized:
            raise ValueError("Destination model is not initialized.")

        if not self.dst_model.is_fully_loaded:
            self.dst_model.ensure_fully_loaded()
            raise ValueError(
                self.t(
                    "cmn.err.model_not_fully_loaded",
                    "The model is not fully loaded.",
                ),
            )

        with self.ctx.same_session() as session:
            crt_val = getattr(record, self._name)

            if self.is_simple:
                final_set = self.get_db_records(session, include_top=True)
            else:
                # Create database records for the new records.
                final_set = []
                for m_record in self.inserted.values():
                    m_data = m_record.get_row_data(Qt.ItemDataRole.EditRole)
                    m_fields = self.dst_model.column_fields
                    assert len(m_data) == len(m_fields)
                    rec_values = {}
                    for f_dst, f_data in zip(m_fields, m_data):
                        if f_dst.name in self.implicit_set:
                            continue
                        rec_values[f_dst.name] = f_data
                    db_record = self.dst_model.db_model(**rec_values)
                    final_set.append(db_record)
                    session.add(db_record)

                final_set.extend(
                    self.get_db_records(session, include_top=False)
                )

        if isinstance(crt_val, set):
            final_set = set(final_set)
        elif isinstance(crt_val, list):
            final_set = list(final_set)
        elif isinstance(crt_val, tuple):
            final_set = tuple(final_set)
        else:
            raise ValueError(
                "Expected a set, list, or tuple, got %s",
                type(crt_val).__name__,
            )
        setattr(record, self._name, final_set)

    def load_value_from(self, record: Any):
        """Load the field value from the database record."""
        if not self._name:
            raise ValueError("Field name is not set.")
        if not self.form:
            raise ValueError("Form is not set for %s", self.__class__.__name__)
        if record is None:
            self.change_field_value(None)
            return

        crt_rec = list(getattr(record, self._name))
        # if isinstance(crt_rec, InstrumentedSet):
        #     crt_rec = set(crt_rec)
        # elif isinstance(crt_rec, InstrumentedList):
        #     crt_rec = list(crt_rec)
        # else:
        #     raise ValueError(
        #         "Expected a set, list, or tuple, got %s",
        #         type(crt_rec).__name__,
        #     )

        if self.is_simple:
            self.dst_model.base_selection = (
                select(self.src_model.db_model)
                .join(getattr(record.__class__, self._name))
                .where(
                    getattr(self.final_db_model, "id")
                    == self.form.get_id_of_record(record)
                )
            )
            self.dst_model.reset_model()
            self._change_field_value(crt_rec)
        else:
            self.change_field_value(crt_rec)
