# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.

from typing import TYPE_CHECKING

from exdrf_qt.models import QtModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from exdrf_dev.qt.tags.fields.id_field import IdField
from exdrf_dev.qt.tags.fields.name_field import NameField
from exdrf_dev.qt.tags.fields.parents_field import ParentsField

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy import Select  # noqa: F401

    from exdrf_dev.db.models import Tag  # noqa: F401


class QtTagFuMo(QtModel["Tag"]):
    """The model that contains all the fields of the Tag table."""

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.db.models import Parent as DbParent
        from exdrf_dev.db.models import Tag as DbTag

        super().__init__(
            ctx=ctx,
            db_model=DbTag,
            selection=select(DbTag).options(
                selectinload(
                    DbTag.parents,
                ).load_only(
                    DbParent.id,
                    DbParent.name,
                )
            ),
            fields=[
                IdField(resource=self),  # type: ignore
                NameField(resource=self),  # type: ignore
                ParentsField(resource=self),  # type: ignore
            ],
            **kwargs,
        )
