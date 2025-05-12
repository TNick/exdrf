# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/m_ocm.py.j2
# Don't change it manually.
from typing import TYPE_CHECKING, Union

from sqlalchemy import select
from sqlalchemy.orm import joinedload, load_only

from exdrf_dev.qt_gen.db.children.fields.fld_data import DataField
from exdrf_dev.qt_gen.db.children.fields.fld_id import IdField
from exdrf_dev.qt_gen.db.children.fields.fld_parent import ParentField
from exdrf_dev.qt_gen.db.children.fields.fld_parent_id import ParentIdField
from exdrf_dev.qt_gen.db.children.fields.single_f import LabelField
from exdrf_dev.qt_gen.db.children.models.child_ful import QtChildFuMo

if TYPE_CHECKING:
    from sqlalchemy import Select  # noqa: F401


class QtChildNaMo(QtChildFuMo):
    """The model that contains only the label field of the
    Child table.

    This model is suitable for a selector or a combobox.
    """

    def __init__(
        self, selection: Union["Select", None] = None, fields=None, **kwargs
    ):
        from exdrf_dev.db.api import Child as DbChild
        from exdrf_dev.db.api import Parent as DbParent

        super().__init__(
            selection=(
                selection
                if selection is not None
                else select(DbChild)
                .options(
                    load_only(
                        DbChild.data,
                        DbChild.id,
                    )
                )
                .options(
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
                    LabelField,
                ]
            ),
            **kwargs,
        )
        self.column_fields = ["label"]
