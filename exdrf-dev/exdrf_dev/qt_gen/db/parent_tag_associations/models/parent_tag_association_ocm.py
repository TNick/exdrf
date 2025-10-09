# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> c/m/m_ocm.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING, Union

from exdrf_qt.plugins import exdrf_qt_pm
from exdrf_qt.utils.plugins import safe_hook_call
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

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from sqlalchemy import Select  # noqa: F401

# exdrf-keep-start other_globals ----------------------------------------------

# exdrf-keep-end other_globals ------------------------------------------------


def default_parent_tag_association_ocm_selection():
    from exdrf_dev.db.api import ParentTagAssociation as DbParentTagAssociation

    return select(DbParentTagAssociation).options(
        load_only(
            DbParentTagAssociation.parent_id,
            DbParentTagAssociation.tag_id,
        )
    )


class QtParentTagAssociationNaMo(QtParentTagAssociationFuMo):
    """The model that contains only the label field of the
    ParentTagAssociation table.

    This model is suitable for a selector or a combobox.
    """

    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------

    def __init__(
        self, selection: Union["Select", None] = None, fields=None, **kwargs
    ):
        pass

        super().__init__(
            selection=(
                selection
                if selection is not None
                else default_parent_tag_association_ocm_selection()
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

        # Inform plugins that the model has been created.
        safe_hook_call(
            exdrf_qt_pm.hook.parent_tag_association_namo_created, model=self
        )

        # exdrf-keep-start extra_init -----------------------------------------

        # exdrf-keep-end extra_init -------------------------------------------

    # exdrf-keep-start extra_namo_content -------------------------------------

    # exdrf-keep-end extra_namo_content ---------------------------------------


# exdrf-keep-start more_content -----------------------------------------------

# exdrf-keep-end more_content -------------------------------------------------
