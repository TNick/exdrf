# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> c/m/w/list.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING

from exdrf_qt.controls.table_list import ListDb

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401

    from exdrf_dev.db.api import RelatedItem  # noqa: F401


class QtRelatedItemList(ListDb["RelatedItem"]):
    """Presents a list of records from the database."""

    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------

    def __init__(self, ctx: "QtContext", *args, **kwargs):
        from exdrf_dev.qt_gen.db.related_items.api import (
            QtRelatedItemFuMo,
        )

        super().__init__(ctx=ctx, *args, **kwargs)
        self.setModel(
            ctx.get_c_ovr(
                "exdrf_dev.qt_gen.db.related_items.list.model",
                QtRelatedItemFuMo,
                ctx=self.ctx,
                parent=self,
            )
        )

        self.setWindowTitle(
            self.t("related_item.tv.title", "Related item list"),
        )

        # exdrf-keep-start extra_init -----------------------------------------

        # exdrf-keep-end extra_init -------------------------------------------

    # exdrf-keep-start extra_list_content ------------------------------------

    # exdrf-keep-end extra_list_content --------------------------------------


# exdrf-keep-start more_content ------------------------------------------------

# exdrf-keep-end more_content --------------------------------------------------
