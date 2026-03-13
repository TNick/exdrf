import logging
from typing import TYPE_CHECKING

from exdrf_qt.field_ed.fed_related import DrfRelated, DrfRelatedType

# exdrf-keep-start other_imports -----------------------------------------------

# exdrf-keep-end other_imports -------------------------------------------------

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy.orm import Session  # noqa: F401

    from exdrf_dev.db.api import Tag as Tag  # noqa: F401

logger = logging.getLogger(__name__)

# exdrf-keep-start other_globals -----------------------------------------------

# exdrf-keep-end other_globals -------------------------------------------------


class QtTagRel(DrfRelated):
    """Relations editor where the target records are Tag instances."""

    # exdrf-keep-start other_attributes ----------------------------------------

    # exdrf-keep-end other_attributes ------------------------------------------

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.db.api import Tag as DbTag
        from exdrf_dev.qt_gen.db.tags.api import (
            QtTagFuMo,
        )

        super().__init__(
            ctx=ctx,
            src_model=kwargs.pop(
                "src_model",
                ctx.get_ovr(
                    "exdrf_dev.qt_gen.db.tags." "rel.src_model.tags",
                    QtTagFuMo,
                ),
            ),
            src_db_model=kwargs.pop(
                "src_db_model",
                ctx.get_ovr(
                    "exdrf_dev.qt_gen.db.tags." "rel.src_db_model.tags",
                    DbTag,
                ),
            ),
            **kwargs,
        )

    # exdrf-keep-start extra_editor_content ------------------------------------

    # exdrf-keep-end extra_editor_content --------------------------------------


class QtParentRelTag(QtTagRel):
    """Relation editor for Tag resources when hosted inside
    Parent resources.

    The editor will present two lists for the user to edit the connections:
        - to the left the full list of Tag resources and
        - to the right the list of Tag resources that are
          associated with the Parent resource that is being edited.
    """

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.db.api import Tag as DbTag
        from exdrf_dev.qt_gen.db.tags.api import (
            QtTagFuMo,
        )

        super().__init__(
            ctx=ctx,
            dst_model=kwargs.pop(
                "dst_model",
                ctx.get_ovr(
                    "exdrf_dev.qt_gen.db.tags."
                    "rel.dst_model.parent_tag_associations",
                    QtTagFuMo,
                ),
            ),
            dst_db_model=kwargs.pop(
                "dst_db_model",
                ctx.get_ovr(
                    "exdrf_dev.qt_gen.db.tags."
                    "rel.dst_db_model.parent_tag_associations",
                    DbTag,
                ),
            ),
            variant=DrfRelatedType.SIMPLE,
        )
        # Inform plugins that the editor has been created.
        # safe_hook_call(
        #    exdrf_qt_pm.hook.parent_rel_tag_created,
        #    widget=self
        # )


# exdrf-keep-start more_content ------------------------------------------------

# exdrf-keep-end more_content --------------------------------------------------
