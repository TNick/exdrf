from typing import TYPE_CHECKING, Any, Generic, TypeVar

from PyQt5.QtCore import QModelIndex, Qt

from exdrf_qt.controls.search_list import SearchList
from exdrf_qt.field_ed.base_drop import DropBase

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext
    from exdrf_qt.models import QtModel

DBM = TypeVar("DBM")


class DrfSelOneEditor(DropBase, Generic[DBM]):
    """Editor for selecting a related record.

    The control is a read-only line edit.
    """

    _dropdown: SearchList

    def __init__(
        self, ctx: "QtContext", model: "QtModel[DBM]", **kwargs
    ) -> None:
        super().__init__(ctx=ctx, **kwargs)
        self.setReadOnly(True)
        self._dropdown = SearchList(  # type: ignore[assignment]
            ctx=ctx,
            model=model,
            popup=True,
        )
        self._dropdown.tree.returnPressed.connect(self._on_select)
        self._dropdown.tree.doubleClicked.connect(self._on_select_index)

    @property
    def model(self) -> "QtModel[DBM]":
        """Return the model."""
        return self._dropdown.model

    @model.setter
    def model(self, value: "QtModel[DBM]") -> None:
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
            self.field_value = new_value
            self.set_line_normal()
            self.setText(
                self.t("cmn.bytes_length", "({cnt} bytes)", cnt=len(new_value))
            )
            if self.nullable:
                assert self.ac_clear is not None
                self.ac_clear.setEnabled(True)

    def _show_dropdown(self):
        """Show the dropdown with filtered choices."""

        # Populate with filtered choices
        self._position_dropdown()
        self._dropdown.src_line.setFocus()

    def _on_select_index(self, index: QModelIndex) -> None:
        """Handle the selection of an item in the dropdown."""
        if index.isValid():
            self._on_select(index.row())

    def _on_select(self, row: int) -> None:
        record = self._dropdown.model.cache[row]
        if not record.loaded:
            return
        data = record.get_row_data(role=Qt.ItemDataRole.DisplayRole)
        value = ", ".join([str(d) for d in data if d is not None])
        self.setText(value)
        self._dropdown.hide()
        self.field_value = record.db_id
        self.set_line_normal()

    def set_line_null(self):
        super().set_line_null()
        self._dropdown.tree.setCurrentIndex(QModelIndex())
