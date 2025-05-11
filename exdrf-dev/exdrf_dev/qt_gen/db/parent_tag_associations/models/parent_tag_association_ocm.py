# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/m_ocm.py.j2
# Don't change it manually.
from typing import TYPE_CHECKING, Union

from sqlalchemy import select
from sqlalchemy.orm import load_only

from exdrf_dev.qt_gen.db.parent_tag_associations.fields.fld_parent_id import (
    ParentIdField,
)
from exdrf_dev.qt_gen.db.parent_tag_associations.fields.fld_tag_id import (
    TagIdField,
)
from exdrf_dev.qt_gen.db.parent_tag_associations.fields.single_f import (
    LabelField,
)
from exdrf_dev.qt_gen.db.parent_tag_associations.models.parent_tag_association_ful import (
    QtParentTagAssociationFuMo,
)

if TYPE_CHECKING:
    from sqlalchemy import Select  # noqa: F401


class QtParentTagAssociationNaMo(QtParentTagAssociationFuMo):
    """The model that contains only the label field of the
    ParentTagAssociation table.

    This model is suitable for a selector or a combobox.
    """

    def __init__(
        self, selection: Union["Select", None] = None, fields=None, **kwargs
    ):
        from exdrf_dev.db.api import (
            ParentTagAssociation as DbParentTagAssociation,
        )

        super().__init__(
            selection=(
                selection
                if selection is not None
                else select(DbParentTagAssociation).options(
                    load_only(
                        DbParentTagAssociation.parent_id,
                        DbParentTagAssociation.tag_id,
                    )
                )
            ),
            fields=(
                fields
                if fields is not None
                else [
                    ParentIdField,
                    TagIdField,
                    LabelField,
                ]
            ),
            **kwargs,
        )
        self.column_fields = ["label"]
