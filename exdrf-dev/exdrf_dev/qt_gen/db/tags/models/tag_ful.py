# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> c/m/m_ful.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING, Union

from exdrf_qt.models import QtModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from exdrf_dev.qt_gen.db.tags.fields.fld_id import IdField
from exdrf_dev.qt_gen.db.tags.fields.fld_name import NameField
from exdrf_dev.qt_gen.db.tags.fields.fld_parents import ParentsField

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy import Select  # noqa: F401

    from exdrf_dev.db.api import Tag  # noqa: F401


def default_tag_list_selection():
    from exdrf_dev.db.api import Parent as DbParent
    from exdrf_dev.db.api import Tag as DbTag

    return select(DbTag).options(
        selectinload(DbTag.parents).load_only(
            DbParent.id,
            DbParent.name,
        ),
    )


class QtTagFuMo(QtModel["Tag"]):
    """The model that contains all the fields of the Tag table."""

    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------

    def __init__(
        self,
        ctx: "QtContext",
        selection: Union["Select", None] = None,
        fields=None,
        **kwargs,
    ):
        from exdrf_dev.db.api import Tag as DbTag

        super().__init__(
            ctx=ctx,
            db_model=ctx.get_ovr("exdrf_dev.qt_gen.db.tags.ful.model", DbTag),
            selection=(
                selection
                if selection is not None
                else default_tag_list_selection()
            ),
            fields=(
                fields
                if fields is not None
                else [
                    NameField,
                    ParentsField,
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
