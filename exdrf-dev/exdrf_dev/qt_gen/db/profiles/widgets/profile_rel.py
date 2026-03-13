import logging
from typing import TYPE_CHECKING

from exdrf_qt.field_ed.fed_related import DrfRelated

# exdrf-keep-start other_imports -----------------------------------------------

# exdrf-keep-end other_imports -------------------------------------------------

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy.orm import Session  # noqa: F401

    from exdrf_dev.db.api import Profile as Profile  # noqa: F401

logger = logging.getLogger(__name__)

# exdrf-keep-start other_globals -----------------------------------------------

# exdrf-keep-end other_globals -------------------------------------------------


class QtProfileRel(DrfRelated):
    """Relations editor where the target records are Profile instances."""

    # exdrf-keep-start other_attributes ----------------------------------------

    # exdrf-keep-end other_attributes ------------------------------------------

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.db.api import Profile as DbProfile
        from exdrf_dev.qt_gen.db.profiles.api import (
            QtProfileFuMo,
        )

        super().__init__(
            ctx=ctx,
            src_model=kwargs.pop(
                "src_model",
                ctx.get_ovr(
                    "exdrf_dev.qt_gen.db.profiles." "rel.src_model.profiles",
                    QtProfileFuMo,
                ),
            ),
            src_db_model=kwargs.pop(
                "src_db_model",
                ctx.get_ovr(
                    "exdrf_dev.qt_gen.db.profiles." "rel.src_db_model.profiles",
                    DbProfile,
                ),
            ),
            **kwargs,
        )

    # exdrf-keep-start extra_editor_content ------------------------------------

    # exdrf-keep-end extra_editor_content --------------------------------------


# exdrf-keep-start more_content ------------------------------------------------

# exdrf-keep-end more_content --------------------------------------------------
