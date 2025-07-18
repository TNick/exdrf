# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> c/m/m_ful.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING, Optional, Union

from exdrf_qt.models import QtModel
from exdrf_qt.plugins import exdrf_qt_pm, safe_hook_call
from sqlalchemy import select
from sqlalchemy.orm import joinedload

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

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf.filter import FilterType  # noqa: F401
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy import Select  # noqa: F401

    from exdrf_dev.db.api import RelatedItem  # noqa: F401

# exdrf-keep-start other_globals ----------------------------------------------

# exdrf-keep-end other_globals ------------------------------------------------


def default_related_item_list_selection():
    from exdrf_dev.db.api import CompositeKeyModel as DbCompositeKeyModel
    from exdrf_dev.db.api import RelatedItem as DbRelatedItem

    return select(DbRelatedItem).options(
        joinedload(DbRelatedItem.comp_key_owner).load_only(
            DbCompositeKeyModel.description,
            DbCompositeKeyModel.key_part1,
            DbCompositeKeyModel.key_part2,
        ),
    )


class QtRelatedItemFuMo(QtModel["RelatedItem"]):
    """The model that contains all the fields of the RelatedItem table."""

    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------

    def __init__(
        self,
        ctx: "QtContext",
        selection: Union["Select", None] = None,
        fields=None,
        **kwargs,
    ):
        from exdrf_dev.db.api import RelatedItem as DbRelatedItem

        super().__init__(
            ctx=ctx,
            db_model=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.related_items.ful.model", DbRelatedItem
            ),
            selection=(
                selection
                if selection is not None
                else default_related_item_list_selection()
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
                ]
            ),
            **kwargs,
        )

        # Inform plugins that the model has been created.
        safe_hook_call(exdrf_qt_pm.hook.related_item_fumo_created, model=self)

    def text_to_filter(
        self,
        text: str,
        exact: Optional[bool] = False,
        limit: Optional[str] = None,
    ) -> "FilterType":
        """Convert a text to a filter.

        The function converts a text to a filter. The text is converted to a
        filter using the `simple_search_fields` property.
        """
        filters = super().text_to_filter(text, exact, limit)
        safe_hook_call(exdrf_qt_pm.hook.related_item_fumo_ttf, model=self)
        return filters

        # exdrf-keep-start extra_init -----------------------------------------

        # exdrf-keep-end extra_init -------------------------------------------

    # exdrf-keep-start extra_fumo_content -------------------------------------

    # exdrf-keep-end extra_fumo_content ---------------------------------------


# exdrf-keep-start more_content -----------------------------------------------

# exdrf-keep-end more_content -------------------------------------------------
