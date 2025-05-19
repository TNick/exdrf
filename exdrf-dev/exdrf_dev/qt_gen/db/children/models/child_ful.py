# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/m_ful.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING, Union

from exdrf_qt.models import QtModel
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from exdrf_dev.qt_gen.db.children.fields.fld_data import DataField
from exdrf_dev.qt_gen.db.children.fields.fld_id import IdField
from exdrf_dev.qt_gen.db.children.fields.fld_parent import ParentField
from exdrf_dev.qt_gen.db.children.fields.fld_parent_id import ParentIdField

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy import Select  # noqa: F401

    from exdrf_dev.db.api import Child  # noqa: F401


class QtChildFuMo(QtModel["Child"]):
    """The model that contains all the fields of the Child table."""

    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------

    def __init__(
        self,
        ctx: "QtContext",
        selection: Union["Select", None] = None,
        fields=None,
        **kwargs,
    ):
        from exdrf_dev.db.api import Child as DbChild
        from exdrf_dev.db.api import Parent as DbParent

        super().__init__(
            ctx=ctx,
            db_model=DbChild,
            selection=(
                selection
                if selection is not None
                else select(DbChild).options(
                    joinedload(DbChild.parent).load_only(
                        DbParent.id,
                        DbParent.name,
                    ),
                )
            ),
            fields=(
                fields
                if fields is not None
                else [
                    DataField,
                    ParentField,
                    ParentIdField,
                    IdField,
                ]
            ),
            **kwargs,
        )

        # exdrf-keep-start extra_init -----------------------------------------

        # exdrf-keep-end extra_init -------------------------------------------

    # exdrf-keep-start extra_fumo_content -------------------------------------

    # exdrf-keep-end extra_fumo_content ---------------------------------------


# exdrf-keep-start more_content -----------------------------------------------

# exdrf-keep-end more_content -------------------------------------------------
