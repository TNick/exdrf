# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/m_ful.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING, Union

from exdrf_qt.models import QtModel
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from exdrf_dev.qt_gen.db.parents.fields.fld_children import ChildrenField
from exdrf_dev.qt_gen.db.parents.fields.fld_created_at import CreatedAtField
from exdrf_dev.qt_gen.db.parents.fields.fld_id import IdField
from exdrf_dev.qt_gen.db.parents.fields.fld_is_active import IsActiveField
from exdrf_dev.qt_gen.db.parents.fields.fld_name import NameField
from exdrf_dev.qt_gen.db.parents.fields.fld_profile import ProfileField
from exdrf_dev.qt_gen.db.parents.fields.fld_tags import TagsField

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy import Select  # noqa: F401

    from exdrf_dev.db.api import Parent  # noqa: F401


class QtParentFuMo(QtModel["Parent"]):
    """The model that contains all the fields of the Parent table."""

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
        from exdrf_dev.db.api import Profile as DbProfile
        from exdrf_dev.db.api import Tag as DbTag

        super().__init__(
            ctx=ctx,
            db_model=DbParent,
            selection=(
                selection
                if selection is not None
                else select(DbParent)
                .options(
                    selectinload(DbParent.children).load_only(
                        DbChild.data,
                        DbChild.id,
                    ),
                    selectinload(DbParent.children)
                    .joinedload(DbChild.parent)
                    .load_only(
                        DbParent.name,
                    ),
                )
                .options(
                    joinedload(DbParent.profile).load_only(
                        DbProfile.bio,
                        DbProfile.id,
                    ),
                )
                .options(
                    selectinload(DbParent.tags).load_only(
                        DbTag.id,
                        DbTag.name,
                    ),
                )
            ),
            fields=(
                fields
                if fields is not None
                else [
                    ChildrenField,
                    CreatedAtField,
                    IsActiveField,
                    NameField,
                    ProfileField,
                    TagsField,
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
