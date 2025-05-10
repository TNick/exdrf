# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/m_ful.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING

from exdrf_qt.models import QtModel
from sqlalchemy import select

from exdrf_dev.qt_gen.db.tags.fields.fld_id import IdField
from exdrf_dev.qt_gen.db.tags.fields.fld_name import NameField
from exdrf_dev.qt_gen.db.tags.fields.fld_parents import ParentsField

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy import Select  # noqa: F401

    from exdrf_dev.db.api import Tag  # noqa: F401


class QtTagFuMo(QtModel["Tag"]):
    """The model that contains all the fields of the Tag table."""

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.db.api import Tag as DbTag

        super().__init__(
            ctx=ctx,
            db_model=DbTag,
            selection=select(DbTag),
            fields=[
                IdField,  # type: ignore
                NameField,  # type: ignore
                ParentsField,  # type: ignore
            ],
            **kwargs,
        )
