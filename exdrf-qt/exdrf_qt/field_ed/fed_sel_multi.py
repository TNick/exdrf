import logging
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    List,
    Optional,
    Set,
    Type,
    TypeVar,
    cast,
)

from exdrf.constants import RecIdType
from PyQt5.QtCore import Qt
from sqlalchemy import inspect

from exdrf_qt.controls.search_list import SearchList
from exdrf_qt.field_ed.base_drop import DropBase

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext
    from exdrf_qt.controls.base_editor import ExdrfEditor
    from exdrf_qt.models import QtModel
    from exdrf_qt.models.record import QtRecord

DBM = TypeVar("DBM")
logger = logging.getLogger(__name__)


class DrfSelMultiEditor(DropBase, Generic[DBM]):
    """Editor for selecting related records.

    The control is a read-only line edit.
    """

    _dropdown: SearchList

    def __init__(
        self,
        ctx: "QtContext",
        qt_model: "QtModel[DBM]",
        editor_class: Optional[Type["ExdrfEditor"]] = None,
        **kwargs,
    ) -> None:
        super().__init__(ctx=ctx, **kwargs)
        self.setReadOnly(True)
        qt_model.checked_ids = set()
        self._dropdown = SearchList(  # type: ignore[assignment]
            ctx=ctx,
            qt_model=qt_model,
            popup=True,
            editor_class=editor_class,
        )
        qt_model.checkedChanged.connect(self.on_checked_ids_changed)

    @property
    def checked_ids(self) -> Set[RecIdType]:
        """Return the checked ids."""
        return self._dropdown.qt_model.checked_ids or set()

    @checked_ids.setter
    def checked_ids(self, value: Set[RecIdType]) -> None:
        """Set the checked ids."""
        self._dropdown.qt_model.checked_ids = value

    @property
    def qt_model(self) -> "QtModel[DBM]":
        """Return the model."""
        return self._dropdown.qt_model

    @qt_model.setter
    def qt_model(self, value: "QtModel[DBM]") -> None:
        """Set the model."""
        self._dropdown.setModel(value)

    def change_field_value(self, new_value: Any) -> None:
        """Change the field value.

        Args:
            new_value: The new value to set. If None, the field is set to NULL.
        """
        if new_value is None:
            self.set_line_null()
            return

        self.field_value = []
        content: List[Any] = []
        not_set = {}
        for itr in new_value:
            if hasattr(itr.__class__, "metadata"):
                itr = self.qt_model.get_db_item_id(itr)
            self.field_value.append(itr)

            # Get the row number of the item in the model.
            row = self.qt_model._db_to_row.get(
                itr, None  # type: ignore[assignment]
            )

            # If the model has loaded the item, add it to the content.
            loaded = False
            if row is not None:
                record = self.qt_model.cache[row]
                if record.loaded:
                    content.append(record)
                    loaded = True

            # If the model has not loaded the item, save the location
            # and add a placeholder.
            if not loaded:
                not_set[itr] = len(content)
                content.append("")  # type: ignore

        # If there are items that are not loaded, load them and add them to
        # the content.
        if len(not_set) > 0:
            ids_to_load = list(not_set.keys())
            for db_item, rec_id in zip(
                self.qt_model.get_db_items_by_id(ids_to_load),
                ids_to_load,
            ):
                if db_item is not None:
                    # Use the model to convert the database item to a record.
                    record = self.qt_model.db_item_to_record(db_item)
                    idx = cast(int, not_set[rec_id])
                    content[idx] = self.record_to_text(record)
                else:
                    logger.debug("No record found for %s", rec_id)

        self.qt_model.set_prioritized_ids(self.field_value)
        self.checked_ids = set(self.field_value)
        self.set_line_normal()
        self.on_checked_ids_changed()
        if self.nullable:
            assert self.ac_clear is not None
            self.ac_clear.setEnabled(True)

    def _show_dropdown(self):
        """Show the dropdown with filtered choices."""
        if self._read_only:
            return
        # Populate with filtered choices
        self._position_dropdown()
        self._dropdown.src_line.setFocus()

    def on_checked_ids_changed(self) -> None:
        """The model informs us that the set of checked items changed."""
        self.setText(
            self.t(
                "cmn.sel_count",
                "{cnt} selected",
                cnt=len(self._dropdown.qt_model.checked_ids),  # type: ignore
            )
        )
        self.field_value = self._dropdown.qt_model.checked_ids
        self.controlChanged.emit()

    def set_line_null(self):
        super().set_line_null()
        self._dropdown.qt_model.checked_ids = set()

    def record_to_text(self, record: "QtRecord") -> str:
        """Convert a record to text."""
        data = record.get_row_data(role=Qt.ItemDataRole.DisplayRole)
        value = ", ".join([str(d) for d in data if d is not None])
        return value

    def save_value_to(self, record: Any):
        """Save the field value into the target record.

        Attributes:
            record: The item to save the field value to.
        """
        if not self._name:
            raise ValueError("Field name is not set.")
        crt_val = getattr(record, self._name, None)
        if self.field_value is None:
            if crt_val is not None:
                crt_val.clear()
            else:
                setattr(record, self._name, None)
            return
        db_lst = [
            d
            for d in self.qt_model.get_db_items_by_id(self.field_value)
            if d is not None
        ]
        # As the value may be either a list or a set, let the class decide
        # what to do.
        if crt_val is not None:
            setattr(record, self._name, crt_val.__class__(db_lst))
        else:
            mapper = inspect(record.__class__)
            relationship = mapper.relationships[self._name]
            setattr(record, self._name, relationship.collection_class(db_lst))

    def load_value_from(self, record: Any):
        """Load the field value from the database record.

        Attributes:
            record: The item to load the field value from.
        """
        if not self._name:
            raise ValueError("Field name is not set.")
        related_list = getattr(record, self._name, None)
        related: List[RecIdType]
        if related_list is None:
            related = []
        else:
            related = []
            for r in related_list:
                related.append(self.qt_model.get_db_item_id(r))

        self.change_field_value(related)
