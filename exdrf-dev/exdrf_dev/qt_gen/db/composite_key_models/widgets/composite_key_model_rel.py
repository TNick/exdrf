import logging
from typing import TYPE_CHECKING

from exdrf_qt.field_ed.fed_related import DrfRelated

# exdrf-keep-start other_imports -----------------------------------------------

# exdrf-keep-end other_imports -------------------------------------------------

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401

    from exdrf_dev.db.api import (  # noqa: F401
        CompositeKeyModel as CompositeKeyModel,
    )

logger = logging.getLogger(__name__)

# exdrf-keep-start other_globals -----------------------------------------------

# exdrf-keep-end other_globals -------------------------------------------------


class QtCompositeKeyModelRel(DrfRelated):
    """Relations editor where the target records are CompositeKeyModel
    instances.

    Attributes:
        src_model: The model of the source record.
        src_db_model: The database model of the source record.
    """

    # exdrf-keep-start other_attributes ----------------------------------------

    # exdrf-keep-end other_attributes ------------------------------------------

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.db.api import CompositeKeyModel as DbCompositeKeyModel
        from exdrf_dev.qt_gen.db.composite_key_models.api import (
            QtCompositeKeyModelFuMo,
        )

        super().__init__(
            ctx=ctx,
            src_model=kwargs.pop(
                "src_model",
                ctx.get_ovr(
                    "exdrf_dev.qt_gen.db.composite_key_models."
                    "rel.src_model.composite_key_models",
                    QtCompositeKeyModelFuMo,
                ),
            ),
            src_db_model=kwargs.pop(
                "src_db_model",
                ctx.get_ovr(
                    "exdrf_dev.qt_gen.db.composite_key_models."
                    "rel.src_db_model.composite_key_models",
                    DbCompositeKeyModel,
                ),
            ),
            **kwargs,
        )

    # exdrf-keep-start extra_editor_content ------------------------------------

    # exdrf-keep-end extra_editor_content --------------------------------------


# exdrf-keep-start more_content ------------------------------------------------

# exdrf-keep-end more_content --------------------------------------------------
