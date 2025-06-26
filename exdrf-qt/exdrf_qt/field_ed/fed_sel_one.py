from typing import TYPE_CHECKING, Any, Generic, Optional, Type, TypeVar

from PyQt5.QtCore import QModelIndex, Qt

from exdrf_qt.controls.search_list import SearchList
from exdrf_qt.field_ed.base_drop import DropBase

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext
    from exdrf_qt.controls.base_editor import EditorDb
    from exdrf_qt.models import QtModel
    from exdrf_qt.models.record import QtRecord

DBM = TypeVar("DBM")


class DrfSelOneEditor(DropBase, Generic[DBM]):
    """Editor for selecting a related record.

    The control is a read-only line edit.
    """

    _dropdown: SearchList

    def __init__(
        self,
        ctx: "QtContext",
        qt_model: "QtModel[DBM]",
        editor_class: Optional[Type["EditorDb"]] = None,
        **kwargs,
    ) -> None:
        super().__init__(ctx=ctx, **kwargs)
        self.setReadOnly(True)
        self._dropdown = SearchList(  # type: ignore[assignment]
            ctx=ctx,
            qt_model=qt_model,
            popup=True,
            editor_class=editor_class,
        )
        self._dropdown.tree.returnPressed.connect(self._on_select)
        self._dropdown.tree.doubleClicked.connect(self._on_select_index)

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

        self.field_value = new_value
        self.set_line_normal()

        # Attempt to locate the record in the model.
        loaded = False
        row = self.qt_model._db_to_row.get(new_value, None)
        if row is not None:
            record = self.qt_model.cache[row]
            if record.loaded:
                self.setText(self.record_to_text(record))
                loaded = True

        if not loaded:
            # If the record is not loaded, we need to load it ourselves.
            with self.qt_model.get_one_db_item_by_id(new_value) as db_item:
                if db_item is None:
                    self.set_line_null()
                    return
                record = self.qt_model.db_item_to_record(db_item)
                self.setText(self.record_to_text(record))

        self.qt_model.set_prioritized_ids([new_value])
        self.set_line_normal()
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

    def _on_select_index(self, index: QModelIndex) -> None:
        """Handle the selection of an item in the dropdown."""
        if index.isValid():
            self._on_select(index.row())

    def _on_select(self, row: int) -> None:
        record = self._dropdown.qt_model.cache[row]
        if not record.loaded:
            return

        self.setText(self.record_to_text(record))
        self._dropdown.hide()
        self.field_value = record.db_id
        self.set_line_normal()
        self.controlChanged.emit()

    def set_line_null(self):
        super().set_line_null()
        self._dropdown.tree.setCurrentIndex(QModelIndex())

    def record_to_text(self, record: "QtRecord") -> str:
        """Convert a record to text."""
        data = record.get_row_data(role=Qt.ItemDataRole.DisplayRole)
        value = ", ".join([str(d) for d in data if d is not None])
        return value
