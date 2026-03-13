import logging
from typing import TYPE_CHECKING

from exdrf_qt.field_ed.fed_related import DrfRelated

# exdrf-keep-start other_imports -----------------------------------------------

# exdrf-keep-end other_imports -------------------------------------------------

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy.orm import Session  # noqa: F401

    from exdrf_dev.db.api import RelatedItem as RelatedItem  # noqa: F401

logger = logging.getLogger(__name__)

# exdrf-keep-start other_globals -----------------------------------------------

# exdrf-keep-end other_globals -------------------------------------------------


class QtRelatedItemRel(DrfRelated):
    """Relations editor where the target records are RelatedItem instances."""

    # exdrf-keep-start other_attributes ----------------------------------------

    # exdrf-keep-end other_attributes ------------------------------------------

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.db.api import RelatedItem as DbRelatedItem
        from exdrf_dev.qt_gen.db.related_items.api import (
            QtRelatedItemFuMo,
        )

        super().__init__(
            ctx=ctx,
            src_model=kwargs.pop(
                "src_model",
                ctx.get_ovr(
                    "exdrf_dev.qt_gen.db.related_items."
                    "rel.src_model.related_items",
                    QtRelatedItemFuMo,
                ),
            ),
            src_db_model=kwargs.pop(
                "src_db_model",
                ctx.get_ovr(
                    "exdrf_dev.qt_gen.db.related_items."
                    "rel.src_db_model.related_items",
                    DbRelatedItem,
                ),
            ),
            **kwargs,
        )

    # exdrf-keep-start extra_editor_content ------------------------------------

    # exdrf-keep-end extra_editor_content --------------------------------------


# exdrf-keep-start more_content ------------------------------------------------

# exdrf-keep-end more_content --------------------------------------------------
