# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> c/m/m_ocm.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING, Union

from exdrf_qt.plugins import exdrf_qt_pm, safe_hook_call
from sqlalchemy import select
from sqlalchemy.orm import load_only

from exdrf_dev.qt_gen.db.related_items.fields.fld_comp_key_owner import (
    CompKeyOwnerField,
)
from exdrf_dev.qt_gen.db.related_items.fields.fld_comp_key_part1 import (
    CompKeyPart1Field,
)
from exdrf_dev.qt_gen.db.related_items.fields.fld_comp_key_part2 import (
    CompKeyPart2Field,
)
from exdrf_dev.qt_gen.db.related_items.fields.fld_id import IdField
from exdrf_dev.qt_gen.db.related_items.fields.fld_item_data import ItemDataField
from exdrf_dev.qt_gen.db.related_items.fields.fld_some_int import SomeIntField
from exdrf_dev.qt_gen.db.related_items.fields.single_f import LabelField
from exdrf_dev.qt_gen.db.related_items.models.related_item_ful import (
    QtRelatedItemFuMo,
)

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from sqlalchemy import Select  # noqa: F401


def default_related_item_ocm_selection():
    from exdrf_dev.db.api import RelatedItem as DbRelatedItem

    return select(DbRelatedItem).options(
        load_only(
            DbRelatedItem.id,
        )
    )


class QtRelatedItemNaMo(QtRelatedItemFuMo):
    """The model that contains only the label field of the
    RelatedItem table.

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
                else default_related_item_ocm_selection()
            ),
            fields=(
                fields
                if fields is not None
                else [
                    CompKeyOwnerField,
                    CompKeyPart1Field,
                    CompKeyPart2Field,
                    ItemDataField,
                    SomeIntField,
                    IdField,
                    LabelField,
                ]
            ),
            **kwargs,
        )
        self.column_fields = ["label"]

        # Inform plugins that the model has been created.
        safe_hook_call(exdrf_qt_pm.hook.related_item_namo_created, model=self)

        # exdrf-keep-start extra_init -----------------------------------------

        # exdrf-keep-end extra_init -------------------------------------------

    # exdrf-keep-start extra_namo_content -------------------------------------

    # exdrf-keep-end extra_namo_content ---------------------------------------


# exdrf-keep-start more_content -----------------------------------------------

# exdrf-keep-end more_content -------------------------------------------------
