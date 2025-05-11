# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/w/selector.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING

from exdrf_qt.field_ed.fed_sel_multi import DrfSelMultiEditor
from exdrf_qt.field_ed.fed_sel_one import DrfSelOneEditor

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext


class QtParentTagAssociationSiSe(DrfSelOneEditor):
    """Reads the list of records from the database and allows the user to
    select one.
    """

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.qt_gen.db.parent_tag_associations.models.parent_tag_association_ocm import (  # noqa: E501
            QtParentTagAssociationNaMo,
        )

        super().__init__(
            qt_model=QtParentTagAssociationNaMo(ctx=ctx), ctx=ctx, **kwargs
        )
        self.qt_model.setParent(self)


class QtParentTagAssociationMuSe(DrfSelMultiEditor):
    """Reads the list of records from the database and allows the user to
    select multiple records.
    """

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.qt_gen.db.parent_tag_associations.models.parent_tag_association_ocm import (  # noqa: E501
            QtParentTagAssociationNaMo,
        )

        super().__init__(
            qt_model=QtParentTagAssociationNaMo(ctx=ctx), ctx=ctx, **kwargs
        )
        self.qt_model.setParent(self)
