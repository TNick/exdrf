# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> c/m/m_ocm.py.j2
# Don't change it manually.

import logging
from functools import lru_cache
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


@lru_cache(maxsize=1)
def _default_parent_tag_association_ocm_selection_base():
    from exdrf_dev.db.api import ParentTagAssociation as DbParentTagAssociation

    try:
        return select(DbParentTagAssociation).options(
            load_only(
                DbParentTagAssociation.parent_id,
                DbParentTagAssociation.tag_id,
            )
        )
    except Exception:
        logging.getLogger(__name__).error(
            "Error creating default selection for parent_tag_association",
            exc_info=True,
        )
        return select(DbParentTagAssociation)


def default_parent_tag_association_ocm_selection(db_model: object):
    from exdrf_dev.db.api import ParentTagAssociation as DbParentTagAssociation

    # If an override changes the ORM model class, the statically generated
    # eager-loading options will not match. Fall back to a plain select on the
    # overridden model to keep the query valid on all dialects.
    if db_model is not DbParentTagAssociation:
        return select(db_model)

    return _default_parent_tag_association_ocm_selection_base()


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
        from exdrf_dev.db.api import (
            ParentTagAssociation as DbParentTagAssociation,
        )

        super().__init__(
            selection=(
                selection
                if selection is not None
                else default_parent_tag_association_ocm_selection(
                    kwargs.get("db_model", DbParentTagAssociation)
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
        self.remove_from_ssf("label")

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
