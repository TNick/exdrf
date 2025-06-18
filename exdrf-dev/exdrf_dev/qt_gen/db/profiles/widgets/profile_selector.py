# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> c/m/w/selector.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING

from exdrf_qt.field_ed.fed_sel_multi import DrfSelMultiEditor
from exdrf_qt.field_ed.fed_sel_one import DrfSelOneEditor
from exdrf_qt.plugins import exdrf_qt_pm, safe_hook_call

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401


class QtProfileSiSe(DrfSelOneEditor):
    """Reads the list of records from the database and allows the user to
    select one.
    """

    # exdrf-keep-start other_sise_attributes ----------------------------------

    # exdrf-keep-end other_sise_attributes ------------------------------------

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.qt_gen.db.profiles.models.profile_ocm import (  # noqa: E501
            QtProfileNaMo,
        )

        super().__init__(
            qt_model=ctx.get_c_ovr(
                "exdrf_dev.qt_gen.db.profiles.selector.model",
                QtProfileNaMo,
                ctx=ctx,
            ),
            ctx=ctx,
            **kwargs,
        )
        self.qt_model.setParent(self)

        # Inform plugins that the widget has been created.
        safe_hook_call(exdrf_qt_pm.hook.profile_sise_created, widget=self)

        # exdrf-keep-start extra_sise_init -----------------------------------

        # exdrf-keep-end extra_sise_init -------------------------------------

    # exdrf-keep-start extra_sise_content ------------------------------------

    # exdrf-keep-end extra_sise_content --------------------------------------


class QtProfileMuSe(DrfSelMultiEditor):
    """Reads the list of records from the database and allows the user to
    select multiple records.
    """

    # exdrf-keep-start other_muse_attributes ----------------------------------

    # exdrf-keep-end other_muse_attributes ------------------------------------

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.qt_gen.db.profiles.models.profile_ocm import (  # noqa: E501
            QtProfileNaMo,
        )

        super().__init__(qt_model=QtProfileNaMo(ctx=ctx), ctx=ctx, **kwargs)
        self.qt_model.setParent(self)

        # Inform plugins that the widget has been created.
        safe_hook_call(exdrf_qt_pm.hook.profile_muse_created, widget=self)

        # exdrf-keep-start extra_muse_init -----------------------------------

        # exdrf-keep-end extra_muse_init -------------------------------------

    # exdrf-keep-start extra_muse_content ------------------------------------

    # exdrf-keep-end extra_muse_content --------------------------------------


# exdrf-keep-start more_content ------------------------------------------------

# exdrf-keep-end more_content --------------------------------------------------
