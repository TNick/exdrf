# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/m_ful.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING, Union

from exdrf_qt.models import QtModel
from sqlalchemy import select

from exdrf_dev.qt_gen.db.parent_tag_associations.fields.fld_parent_id import (
    ParentIdField,
)
from exdrf_dev.qt_gen.db.parent_tag_associations.fields.fld_tag_id import (
    TagIdField,
)

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy import Select  # noqa: F401

    from exdrf_dev.db.api import ParentTagAssociation  # noqa: F401


class QtParentTagAssociationFuMo(QtModel["ParentTagAssociation"]):
    """The model that contains all the fields of the ParentTagAssociation table."""

    def __init__(
        self,
        ctx: "QtContext",
        selection: Union["Select", None] = None,
        fields=None,
        **kwargs,
    ):
        from exdrf_dev.db.api import (
            ParentTagAssociation as DbParentTagAssociation,
        )

        super().__init__(
            ctx=ctx,
            db_model=DbParentTagAssociation,
            selection=(
                selection
                if selection is not None
                else select(DbParentTagAssociation)
            ),
            fields=(
                fields
                if fields is not None
                else [
                    ParentIdField,
                    TagIdField,
                ]
            ),
            **kwargs,
        )
