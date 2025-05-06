# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.

from typing import TYPE_CHECKING

from exdrf_qt.models import QtModel
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from exdrf_dev.qt.children.fields.data_field import DataField
from exdrf_dev.qt.children.fields.id_field import IdField
from exdrf_dev.qt.children.fields.parent_field import ParentField
from exdrf_dev.qt.children.fields.parent_id_field import ParentIdField

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy import Select  # noqa: F401

    from exdrf_dev.db.models import Child  # noqa: F401


class QtChildFuMo(QtModel["Child"]):
    """The model that contains all the fields of the Child table."""

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.db.models import Child as DbChild
        from exdrf_dev.db.models import Parent as DbParent

        super().__init__(
            ctx=ctx,
            db_model=DbChild,
            selection=select(DbChild).options(
                joinedload(
                    DbChild.parent,
                ).load_only(
                    DbParent.id,
                    DbParent.name,
                )
            ),
            fields=[
                IdField,
                DataField,
                ParentIdField,
                ParentField,
            ],
            **kwargs,
        )
