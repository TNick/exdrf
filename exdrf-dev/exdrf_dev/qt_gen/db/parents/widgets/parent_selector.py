# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> c/m/w/selector.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING

from exdrf_qt.field_ed.fed_sel_multi import DrfSelMultiEditor
from exdrf_qt.field_ed.fed_sel_one import DrfSelOneEditor

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401


class QtParentSiSe(DrfSelOneEditor):
    """Reads the list of records from the database and allows the user to
    select one.
    """

    # exdrf-keep-start other_sise_attributes ----------------------------------

    # exdrf-keep-end other_sise_attributes ------------------------------------

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.qt_gen.db.parents.models.parent_ocm import (  # noqa: E501
            QtParentNaMo,
        )

        super().__init__(
            qt_model=ctx.get_c_ovr(
                "exdrf_dev.qt_gen.db.parents.selector.model",
                QtParentNaMo,
                ctx=ctx,
            ),
            ctx=ctx,
            **kwargs,
        )
        self.qt_model.setParent(self)
        # exdrf-keep-start extra_sise_init -----------------------------------

        # exdrf-keep-end extra_sise_init -------------------------------------

    # exdrf-keep-start extra_sise_content ------------------------------------

    # exdrf-keep-end extra_sise_content --------------------------------------


class QtParentMuSe(DrfSelMultiEditor):
    """Reads the list of records from the database and allows the user to
    select multiple records.
    """

    # exdrf-keep-start other_muse_attributes ----------------------------------

    # exdrf-keep-end other_muse_attributes ------------------------------------

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.qt_gen.db.parents.models.parent_ocm import (  # noqa: E501
            QtParentNaMo,
        )

        super().__init__(qt_model=QtParentNaMo(ctx=ctx), ctx=ctx, **kwargs)
        self.qt_model.setParent(self)
        # exdrf-keep-start extra_muse_init -----------------------------------

        # exdrf-keep-end extra_muse_init -------------------------------------

    # exdrf-keep-start extra_muse_content ------------------------------------

    # exdrf-keep-end extra_muse_content --------------------------------------


# exdrf-keep-start more_content ------------------------------------------------

# exdrf-keep-end more_content --------------------------------------------------
