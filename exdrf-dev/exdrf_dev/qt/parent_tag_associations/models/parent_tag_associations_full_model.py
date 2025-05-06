# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.

from typing import TYPE_CHECKING

from exdrf_qt.models import QtModel
from sqlalchemy import select

from exdrf_dev.qt.parent_tag_associations.fields.parent_id_field import (
    ParentIdField,
)
from exdrf_dev.qt.parent_tag_associations.fields.tag_id_field import TagIdField

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy import Select  # noqa: F401

    from exdrf_dev.db.models import ParentTagAssociation  # noqa: F401


class QtParentTagAssociationFuMo(QtModel["ParentTagAssociation"]):
    """The model that contains all the fields of the ParentTagAssociation table."""

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.db.models import (
            ParentTagAssociation as DbParentTagAssociation,
        )

        super().__init__(
            ctx=ctx,
            db_model=DbParentTagAssociation,
            selection=select(DbParentTagAssociation),
            fields=[
                ParentIdField,
                TagIdField,
            ],
            **kwargs,
        )
