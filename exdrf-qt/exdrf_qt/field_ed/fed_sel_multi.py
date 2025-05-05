from typing import TYPE_CHECKING, Any, Generic, TypeVar

from exdrf_qt.controls.search_list import SearchList
from exdrf_qt.field_ed.base_drop import DropBase

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext
    from exdrf_qt.models import QtModel

DBM = TypeVar("DBM")


class DrfSelMultiEditor(DropBase, Generic[DBM]):
    """Editor for selecting related records.

    The control is a read-only line edit.
    """

    _dropdown: SearchList

    def __init__(
        self, ctx: "QtContext", model: "QtModel[DBM]", **kwargs
    ) -> None:
        super().__init__(ctx=ctx, **kwargs)
        self.setReadOnly(True)
        model.checked_ids = set()
        self._dropdown = SearchList(  # type: ignore[assignment]
            ctx=ctx,
            model=model,
            popup=True,
        )
        model.checkedChanged.connect(self.set_checked_ids)

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

    def set_checked_ids(self) -> None:
        """The model informs us that the set of checked items changed."""
        self.setText(
            self.t(
                "cmn.sel_count",
                "{cnt} selected",
                cnt=len(self._dropdown.model.checked_ids),
            )
        )

    def set_line_null(self):
        super().set_line_null()
        self._dropdown.model.checked_ids = set()
