# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> c/m/w/list.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING

from exdrf_qt.controls.table_list import ListDb

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf_dev.db.api import Child  # noqa: F401


class QtChildList(ListDb["Child"]):
    """Presents a list of records from the database."""

    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------

    def __init__(self, *args, **kwargs):
        from exdrf_dev.qt_gen.db.children.api import (
            QtChildEditor,
            QtChildFuMo,
            QtChildTv,
        )

        super().__init__(
            editor=QtChildEditor, viewer=QtChildTv, *args, **kwargs
        )
        self.setModel(
            QtChildFuMo(
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
