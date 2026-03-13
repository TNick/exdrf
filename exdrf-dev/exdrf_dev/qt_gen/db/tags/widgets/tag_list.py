# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> c/m/w/list.py.j2
# Don't change it manually.

import logging
from typing import TYPE_CHECKING, Type

from exdrf_qt.controls.table_list import ListDb
from exdrf_qt.plugins import exdrf_qt_pm
from exdrf_qt.utils.plugins import safe_hook_call

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf_qt.comparator.widgets.record_cmp_base import RecordComparatorBase
    from exdrf_qt.context import QtContext  # noqa: F401

    from exdrf_dev.db.api import Tag  # noqa: F401

# exdrf-keep-start other_globals ----------------------------------------------

# exdrf-keep-end other_globals ------------------------------------------------

logger = logging.getLogger(__name__)


class QtTagList(ListDb["Tag"]):
    """Presents a list of records from the database."""

    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------

    def __init__(self, ctx: "QtContext", *args, **kwargs):
        from exdrf_dev.qt_gen.db.tags.api import (
            QtTagFuMo,
        )

        super().__init__(
            ctx=ctx,
            *args,
            other_actions=kwargs.pop(
                "other_actions",
                ctx.get_ovr("exdrf_dev.qt_gen.db.tags.list.extra-menus", None),
            ),
            compare_merge_enabled=kwargs.pop(
                "compare_merge_enabled",
                ctx.get_ovr("list.compare_merge_enabled", True),
            ),
            compare_merge_max_selection=kwargs.pop(
                "compare_merge_max_selection",
                ctx.get_ovr("list.compare_merge_max_selection", 10),
            ),
            **kwargs,
        )
        self.setModel(
            ctx.get_c_ovr(
                "exdrf_dev.qt_gen.db.tags.list.model",
                QtTagFuMo,
                ctx=self.ctx,
                parent=self,
            )
        )

        self.setWindowTitle(
            self.t("tag.list.title", "Tag list"),
        )

        # Inform plugins that the list has been created.
        safe_hook_call(exdrf_qt_pm.hook.tag_list_created, widget=self)

        # exdrf-keep-start extra_init -----------------------------------------

        # exdrf-keep-end extra_init -------------------------------------------

    def compare_merge_widget_class(self) -> Type["RecordComparatorBase"]:
        from .tag_cmp import QtTagCmp

        return QtTagCmp

    # exdrf-keep-start extra_list_content ------------------------------------

    # exdrf-keep-end extra_list_content --------------------------------------


# exdrf-keep-start more_content ------------------------------------------------

# exdrf-keep-end more_content --------------------------------------------------
