# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.

from typing import TYPE_CHECKING

from exdrf_qt.widgets import MultiSelDb, SingleSelDb

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext


class QtParentSiSe(SingleSelDb):
    """Reads the list of records from the database and allows the user to
    select one.
    """

    def __init__(self, ctx: "QtContext", **kwargs):
        from ..models.parents_one_col_model import QtParentNaMo

        super().__init__(qt_model=QtParentNaMo(ctx=ctx), ctx=ctx, **kwargs)
        self.qt_model.setParent(self)


class QtParentMuSe(MultiSelDb):
    """Reads the list of records from the database and allows the user to
    select multiple records.
    """

    def __init__(self, ctx: "QtContext", **kwargs):
        from ..models.parents_one_col_model import QtParentNaMo

        super().__init__(qt_model=QtParentNaMo(ctx=ctx), ctx=ctx, **kwargs)
        self.qt_model.setParent(self)
