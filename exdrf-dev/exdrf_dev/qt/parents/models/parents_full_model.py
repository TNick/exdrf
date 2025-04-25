# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.

from typing import TYPE_CHECKING

from exdrf_qt.models import QtModel
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from exdrf_dev.qt.parents.fields.children_field import ChildrenField
from exdrf_dev.qt.parents.fields.created_at_field import CreatedAtField
from exdrf_dev.qt.parents.fields.id_field import IdField
from exdrf_dev.qt.parents.fields.is_active_field import IsActiveField
from exdrf_dev.qt.parents.fields.name_field import NameField
from exdrf_dev.qt.parents.fields.profile_field import ProfileField
from exdrf_dev.qt.parents.fields.tags_field import TagsField

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy import Select  # noqa: F401

    from exdrf_dev.db.models import Parent  # noqa: F401


class QtParentFuMo(QtModel["Parent"]):
    """The model that contains all the fields of the Parent table."""

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.db.models import Child as DbChild
        from exdrf_dev.db.models import Parent as DbParent
        from exdrf_dev.db.models import Profile as DbProfile
        from exdrf_dev.db.models import Tag as DbTag

        super().__init__(
            ctx=ctx,
            db_model=DbParent,
            selection=select(DbParent)
            .options(
                selectinload(
                    DbParent.children,
                ).load_only(
                    DbChild.data,
                    DbChild.id,
                )
            )
            .options(
                joinedload(
                    DbParent.profile,
                ).load_only(
                    DbProfile.bio,
                    DbProfile.id,
                )
            )
            .options(
                selectinload(
                    DbParent.tags,
                ).load_only(
                    DbTag.id,
                    DbTag.name,
                )
            ),
            fields=[
                IdField(resource=self),  # type: ignore
                NameField(resource=self),  # type: ignore
                CreatedAtField(resource=self),  # type: ignore
                IsActiveField(resource=self),  # type: ignore
                ChildrenField(resource=self),  # type: ignore
                ProfileField(resource=self),  # type: ignore
                TagsField(resource=self),  # type: ignore
            ],
            **kwargs,
        )
