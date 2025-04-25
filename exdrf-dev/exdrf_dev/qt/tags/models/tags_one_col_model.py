# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.

from typing import TYPE_CHECKING

from exdrf_qt.models import QtModel

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy import Select  # noqa: F401

    from exdrf_dev.db.models import Tag  # noqa: F401


class QtTagNaMo(QtModel["Tag"]):
    """The model that contains only the label field of the
    Tag table.
    """

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.db.models import Tag as DbTag

        super().__init__(ctx=ctx, db_model=DbTag, fields=[], **kwargs)
