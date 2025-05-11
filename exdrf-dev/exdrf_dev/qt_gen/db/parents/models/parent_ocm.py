# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/m_ocm.py.j2
# Don't change it manually.
from typing import TYPE_CHECKING, Union

from sqlalchemy import select
from sqlalchemy.orm import load_only

from exdrf_dev.qt_gen.db.parents.fields.fld_children import ChildrenField
from exdrf_dev.qt_gen.db.parents.fields.fld_created_at import CreatedAtField
from exdrf_dev.qt_gen.db.parents.fields.fld_id import IdField
from exdrf_dev.qt_gen.db.parents.fields.fld_is_active import IsActiveField
from exdrf_dev.qt_gen.db.parents.fields.fld_name import NameField
from exdrf_dev.qt_gen.db.parents.fields.fld_profile import ProfileField
from exdrf_dev.qt_gen.db.parents.fields.fld_tags import TagsField
from exdrf_dev.qt_gen.db.parents.fields.single_f import LabelField
from exdrf_dev.qt_gen.db.parents.models.parent_ful import QtParentFuMo

if TYPE_CHECKING:
    from sqlalchemy import Select  # noqa: F401


class QtParentNaMo(QtParentFuMo):
    """The model that contains only the label field of the
    Parent table.

    This model is suitable for a selector or a combobox.
    """

    def __init__(
        self, selection: Union["Select", None] = None, fields=None, **kwargs
    ):
        from exdrf_dev.db.api import Parent as DbParent

        super().__init__(
            selection=(
                selection
                if selection is not None
                else select(DbParent).options(
                    load_only(
                        DbParent.id,
                        DbParent.name,
                    )
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
                    LabelField,
                ]
            ),
            **kwargs,
        )
        self.column_fields = ["label"]
