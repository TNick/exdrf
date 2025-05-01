from typing import TYPE_CHECKING

from exdrf_qt.widgets.common.date import DateLineEdit
from exdrf_qt.widgets.field_ed.fed_base import DBM, DrfFieldEditor

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext


class DrfDateEditor(DateLineEdit, DrfFieldEditor[DBM]):
    """Editor for dates."""

    def __init__(self, ctx: "QtContext", parent=None) -> None:
        super().__init__(parent, ctx=ctx)  # type: ignore

    def read_value(self, record: DBM) -> None:
        value = self._get_value(record)
        if value is None:
            self.clear_to_null()
        else:
            self._is_null = False
            self.setDate(value)

    def write_value(self, record: DBM) -> None:
        if self._nullable and self._is_null:
            self._set_value(record, None)
        else:
            value = self.date()
            self._set_value(record, value)
