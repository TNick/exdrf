# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> c/m/w/list.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING

from exdrf_qt.controls.table_list import ListDb

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401

    from exdrf_dev.db.api import CompositeKeyModel  # noqa: F401


class QtCompositeKeyModelList(ListDb["CompositeKeyModel"]):
    """Presents a list of records from the database."""

    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------

    def __init__(self, ctx: "QtContext", *args, **kwargs):
        from exdrf_dev.qt_gen.db.composite_key_models.api import (
            QtCompositeKeyModelEditor,
            QtCompositeKeyModelFuMo,
            QtCompositeKeyModelTv,
        )

        super().__init__(
            editor=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.composite_key_models.list.editor",
                QtCompositeKeyModelEditor,
            ),
            viewer=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.composite_key_models.list.viewer",
                QtCompositeKeyModelTv,
            ),
            ctx=ctx,
            *args,
            **kwargs,
        )
        self.setModel(
            ctx.get_c_ovr(
                "exdrf_dev.qt_gen.db.composite_key_models.list.model",
                QtCompositeKeyModelFuMo,
                ctx=self.ctx,
                parent=self,
            )
        )
        # exdrf-keep-start extra_init -----------------------------------------

        # exdrf-keep-end extra_init -------------------------------------------

    # exdrf-keep-start extra_list_content ------------------------------------

    # exdrf-keep-end extra_list_content --------------------------------------


# exdrf-keep-start more_content ------------------------------------------------

# exdrf-keep-end more_content --------------------------------------------------
