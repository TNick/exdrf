# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/w/selector.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING

from exdrf_qt.controls import MultiSelDb, SingleSelDb

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext


class QtParentSiSe(SingleSelDb):
    """Reads the list of records from the database and allows the user to
    select one.
    """

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.qt_gen.db.parents.models.parent_ocm import (  # noqa: E501
            QtParentNaMo,
        )

        super().__init__(qt_model=QtParentNaMo(ctx=ctx), ctx=ctx, **kwargs)
        self.qt_model.setParent(self)


class QtParentMuSe(MultiSelDb):
    """Reads the list of records from the database and allows the user to
    select multiple records.
    """

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.qt_gen.db.parents.models.parent_ocm import (  # noqa: E501
            QtParentNaMo,
        )

        super().__init__(qt_model=QtParentNaMo(ctx=ctx), ctx=ctx, **kwargs)
        self.qt_model.setParent(self)
