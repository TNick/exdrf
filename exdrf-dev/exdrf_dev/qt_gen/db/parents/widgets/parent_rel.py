import logging
from typing import TYPE_CHECKING

from exdrf_qt.field_ed.fed_related import DrfRelated, DrfRelatedType

# exdrf-keep-start other_imports -----------------------------------------------

# exdrf-keep-end other_imports -------------------------------------------------

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy.orm import Session  # noqa: F401

    from exdrf_dev.db.api import Parent as Parent  # noqa: F401

logger = logging.getLogger(__name__)

# exdrf-keep-start other_globals -----------------------------------------------

# exdrf-keep-end other_globals -------------------------------------------------


class QtParentRel(DrfRelated):
    """Relations editor where the target records are Parent instances."""

    # exdrf-keep-start other_attributes ----------------------------------------

    # exdrf-keep-end other_attributes ------------------------------------------

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.db.api import Parent as DbParent
        from exdrf_dev.qt_gen.db.parents.api import (
            QtParentFuMo,
        )

        super().__init__(
            ctx=ctx,
            src_model=kwargs.pop(
                "src_model",
                ctx.get_ovr(
                    "exdrf_dev.qt_gen.db.parents." "rel.src_model.parents",
                    QtParentFuMo,
                ),
            ),
            src_db_model=kwargs.pop(
                "src_db_model",
                ctx.get_ovr(
                    "exdrf_dev.qt_gen.db.parents." "rel.src_db_model.parents",
                    DbParent,
                ),
            ),
            **kwargs,
        )

    # exdrf-keep-start extra_editor_content ------------------------------------

    # exdrf-keep-end extra_editor_content --------------------------------------


class QtTagRelParent(QtParentRel):
    """Relation editor for Parent resources when hosted inside
    Tag resources.

    The editor will present two lists for the user to edit the connections:
        - to the left the full list of Parent resources and
        - to the right the list of Parent resources that are
          associated with the Tag resource that is being edited.
    """

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.db.api import Parent as DbParent
        from exdrf_dev.qt_gen.db.parents.api import (
            QtParentFuMo,
        )

        super().__init__(
            ctx=ctx,
            dst_model=kwargs.pop(
                "dst_model",
                ctx.get_ovr(
                    "exdrf_dev.qt_gen.db.parents."
                    "rel.dst_model.parent_tag_associations",
                    QtParentFuMo,
                ),
            ),
            dst_db_model=kwargs.pop(
                "dst_db_model",
                ctx.get_ovr(
                    "exdrf_dev.qt_gen.db.parents."
                    "rel.dst_db_model.parent_tag_associations",
                    DbParent,
                ),
            ),
            variant=DrfRelatedType.SIMPLE,
        )
        # Inform plugins that the editor has been created.
        # safe_hook_call(
        #    exdrf_qt_pm.hook.tag_rel_parent_created,
        #    widget=self
        # )


# exdrf-keep-start more_content ------------------------------------------------

# exdrf-keep-end more_content --------------------------------------------------
