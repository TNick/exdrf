# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/m_ful.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING

from exdrf_qt.models import QtModel
from sqlalchemy import select

from exdrf_dev.qt_gen.db.profiles.fields.fld_bio import BioField
from exdrf_dev.qt_gen.db.profiles.fields.fld_id import IdField
from exdrf_dev.qt_gen.db.profiles.fields.fld_parent import ParentField
from exdrf_dev.qt_gen.db.profiles.fields.fld_parent_id import ParentIdField

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy import Select  # noqa: F401

    from exdrf_dev.db.api import Profile  # noqa: F401


class QtProfileFuMo(QtModel["Profile"]):
    """The model that contains all the fields of the Profile table."""

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.db.api import Profile as DbProfile

        super().__init__(
            ctx=ctx,
            db_model=DbProfile,
            selection=select(DbProfile),
            fields=[
                BioField,  # type: ignore
                IdField,  # type: ignore
                ParentField,  # type: ignore
                ParentIdField,  # type: ignore
            ],
            **kwargs,
        )
