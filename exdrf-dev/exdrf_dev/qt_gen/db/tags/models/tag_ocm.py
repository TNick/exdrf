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

from exdrf_dev.qt_gen.db.tags.fields.fld_id import IdField
from exdrf_dev.qt_gen.db.tags.fields.fld_name import NameField
from exdrf_dev.qt_gen.db.tags.fields.fld_parents import ParentsField
from exdrf_dev.qt_gen.db.tags.fields.single_f import LabelField
from exdrf_dev.qt_gen.db.tags.models.tag_ful import QtTagFuMo

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from sqlalchemy import Select  # noqa: F401

# exdrf-keep-start other_globals ----------------------------------------------

# exdrf-keep-end other_globals ------------------------------------------------


@lru_cache(maxsize=1)
def _default_tag_ocm_selection_base():
    from exdrf_dev.db.api import Tag as DbTag

    try:
        return select(DbTag).options(
            load_only(
                DbTag.id,
                DbTag.name,
            )
        )
    except Exception:
        logging.getLogger(__name__).error(
            "Error creating default selection for tag",
            exc_info=True,
        )
        return select(DbTag)


def default_tag_ocm_selection(db_model: object):
    from exdrf_dev.db.api import Tag as DbTag

    # If an override changes the ORM model class, the statically generated
    # eager-loading options will not match. Fall back to a plain select on the
    # overridden model to keep the query valid on all dialects.
    if db_model is not DbTag:
        return select(db_model)

    return _default_tag_ocm_selection_base()


class QtTagNaMo(QtTagFuMo):
    """The model that contains only the label field of the
    Tag table.

    This model is suitable for a selector or a combobox.
    """

    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------

    def __init__(
        self, selection: Union["Select", None] = None, fields=None, **kwargs
    ):
        from exdrf_dev.db.api import Tag as DbTag

        super().__init__(
            selection=(
                selection
                if selection is not None
                else default_tag_ocm_selection(kwargs.get("db_model", DbTag))
            ),
            fields=(
                fields
                if fields is not None
                else [
                    NameField,
                    ParentsField,
                    IdField,
                    LabelField,
                ]
            ),
            **kwargs,
        )
        self.column_fields = ["label"]
        self.remove_from_ssf("label")

        # Inform plugins that the model has been created.
        safe_hook_call(exdrf_qt_pm.hook.tag_namo_created, model=self)

        # exdrf-keep-start extra_init -----------------------------------------

        # exdrf-keep-end extra_init -------------------------------------------

    # exdrf-keep-start extra_namo_content -------------------------------------

    # exdrf-keep-end extra_namo_content ---------------------------------------


# exdrf-keep-start more_content -----------------------------------------------

# exdrf-keep-end more_content -------------------------------------------------
