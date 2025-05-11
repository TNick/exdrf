from typing import TYPE_CHECKING, Any, Generic, Set, TypeVar

from exdrf.constants import RecIdType
from PyQt5.QtCore import Qt

from exdrf_qt.controls.search_list import SearchList
from exdrf_qt.field_ed.base_drop import DropBase

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext
    from exdrf_qt.models import QtModel
    from exdrf_qt.models.record import QtRecord

DBM = TypeVar("DBM")


class DrfSelMultiEditor(DropBase, Generic[DBM]):
    """Editor for selecting related records.

    The control is a read-only line edit.
    """

    _dropdown: SearchList

    def __init__(
        self, ctx: "QtContext", qt_model: "QtModel[DBM]", **kwargs
    ) -> None:
        super().__init__(ctx=ctx, **kwargs)
        self.setReadOnly(True)
        qt_model.checked_ids = set()
        self._dropdown = SearchList(  # type: ignore[assignment]
            ctx=ctx,
            qt_model=qt_model,
            popup=True,
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
        else:
            self.field_value = []
            content = []
            not_set = {}
            for itr in new_value:
                if hasattr(itr.__class__, "metadata"):
                    itr = self.qt_model.get_db_item_id(itr)
                self.field_value.append(itr)

                row = self.qt_model._db_to_row.get(
                    itr, None  # type: ignore[assignment]
                )
                loaded = False
                if row is not None:
                    record = self.qt_model.cache[row]
                    if record.loaded:
                        content.append(record)
                        loaded = True
                if not loaded:
                    not_set[itr] = len(content)
                    content.append("")

            if len(not_set) > 0:
                for db_item in self.qt_model.get_db_items_by_id(
                    list(not_set.keys())
                ):
                    if db_item is not None:
                        record = self.qt_model.db_item_to_record(db_item)
                        rec_id = self.qt_model.get_db_item_id(db_item)
                        loc = not_set[rec_id]
                        content[loc] = self.record_to_text(record)

            self.checked_ids = set(self.field_value)
            self.set_line_normal()
            self.on_checked_ids_changed()
            if self.nullable:
                assert self.ac_clear is not None
                self.ac_clear.setEnabled(True)

    def _show_dropdown(self):
        """Show the dropdown with filtered choices."""

        # Populate with filtered choices
        self._position_dropdown()
        self._dropdown.src_line.setFocus()

    def on_checked_ids_changed(self) -> None:
        """The model informs us that the set of checked items changed."""
        self.setText(
            self.t(
                "cmn.sel_count",
                "{cnt} selected",
                cnt=len(self._dropdown.qt_model.checked_ids),
            )
        )
        self.controlChanged.emit()

    def set_line_null(self):
        super().set_line_null()
        self._dropdown.qt_model.checked_ids = set()

    def record_to_text(self, record: "QtRecord") -> str:
        """Convert a record to text."""
        data = record.get_row_data(role=Qt.ItemDataRole.DisplayRole)
        value = ", ".join([str(d) for d in data if d is not None])
        return value
