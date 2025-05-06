# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.

from typing import TYPE_CHECKING

from exdrf_qt.models import QtModel
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from exdrf_dev.qt.profiles.fields.bio_field import BioField
from exdrf_dev.qt.profiles.fields.id_field import IdField
from exdrf_dev.qt.profiles.fields.parent_field import ParentField
from exdrf_dev.qt.profiles.fields.parent_id_field import ParentIdField

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy import Select  # noqa: F401

    from exdrf_dev.db.models import Profile  # noqa: F401


class QtProfileFuMo(QtModel["Profile"]):
    """The model that contains all the fields of the Profile table."""

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.db.models import Parent as DbParent
        from exdrf_dev.db.models import Profile as DbProfile

        super().__init__(
            ctx=ctx,
            db_model=DbProfile,
            selection=select(DbProfile).options(
                joinedload(
                    DbProfile.parent,
                ).load_only(
                    DbParent.id,
                    DbParent.name,
                )
            ),
            fields=[
                IdField,
                BioField,
                ParentIdField,
                ParentField,
            ],
            **kwargs,
        )
