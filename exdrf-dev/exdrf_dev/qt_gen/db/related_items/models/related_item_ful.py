# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> c/m/m_ful.py.j2
# Don't change it manually.

import logging
from functools import lru_cache
from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Union

from exdrf.constants import RecIdType
from exdrf.filter import SearchType
from exdrf_qt.models import QtModel
from exdrf_qt.plugins import exdrf_qt_pm
from exdrf_qt.utils.plugins import safe_hook_call
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


@lru_cache(maxsize=1)
def _default_related_item_list_selection_base():
    from exdrf_dev.db.api import CompositeKeyModel as DbCompositeKeyModel
    from exdrf_dev.db.api import RelatedItem as DbRelatedItem

    try:
        return select(DbRelatedItem).options(
            joinedload(
                DbRelatedItem.comp_key_owner,
            ).load_only(
                DbCompositeKeyModel.description,
                DbCompositeKeyModel.key_part1,
                DbCompositeKeyModel.key_part2,
            ),
        )
    except Exception:
        logging.getLogger(__name__).error(
            "Error creating default selection for related_item",
            exc_info=True,
        )
        return select(DbRelatedItem)


def default_related_item_list_selection(db_model: Any):
    from exdrf_dev.db.api import RelatedItem as DbRelatedItem

    # If an override changes the ORM model class, the statically generated
    # eager-loading options will not match. Fall back to a plain select on the
    # overridden model to keep the query valid on all dialects.
    if db_model is not DbRelatedItem:
        return select(db_model)

    return _default_related_item_list_selection_base()


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

        # Use db_model from kwargs if provided (e.g., from clone_me),
        # otherwise calculate it from context overrides
        db_model = kwargs.pop("db_model", None)
        if db_model is None:
            db_model = ctx.get_ovr(
                "exdrf_dev.qt_gen.db.related_items.ful.model", DbRelatedItem
            )

        super().__init__(
            ctx=ctx,
            db_model=db_model,
            selection=(
                selection
                if selection is not None
                else default_related_item_list_selection(db_model)
            ),
            fields=(
                fields
                if fields is not None
                else [
                    CompKeyPart1Field,
                    CompKeyPart2Field,
                    ItemDataField,
                    SomeIntField,
                    CompKeyOwnerField,
                    IdField,
                ]
            ),
            **kwargs,
        )

        # The fields that are visible in the UI. Excluded from here are
        # the the foreign key fields that are already represented by
        # a resource field and derived fields (e.g. diacritic-less values):
        self.column_fields = [
            "comp_key_part1",
            "comp_key_part2",
            "item_data",
            "some_int",
            "comp_key_owner",
            "id",
        ]

        # Inform plugins that the model has been created.
        safe_hook_call(exdrf_qt_pm.hook.related_item_fumo_created, model=self)

    def get_primary_columns(self) -> Any:
        return self.db_model.id

    def get_db_item_id(
        self, item: "RelatedItem"
    ) -> Union[int, Tuple[int, ...]]:
        return item.id

    def item_by_id_conditions(self, rec_id: RecIdType) -> List[Any]:
        """Return the conditions that filter by ID.

        Args:
            rec_id: The ID of the item to filter by.
        """
        return [self.db_model.id == rec_id]

    def text_to_filter(
        self,
        text: str,
        search_type: Optional[SearchType] = SearchType.EXTENDED,
        limit: Optional[str] = None,
    ) -> "FilterType":
        """Convert a text to a filter.

        The function converts a text to a filter. The text is converted to a
        filter using the `simple_search_fields` property.
        """
        filters = super().text_to_filter(text, search_type, limit)
        safe_hook_call(
            exdrf_qt_pm.hook.related_item_fumo_ttf,
            model=self,
            filters=filters,
            text=text,
            search_type=search_type,
            limit=limit,
        )
        return filters

        # exdrf-keep-start extra_init -----------------------------------------

        # exdrf-keep-end extra_init -------------------------------------------

    # exdrf-keep-start extra_fumo_content -------------------------------------

    # exdrf-keep-end extra_fumo_content ---------------------------------------


# exdrf-keep-start more_content -----------------------------------------------

# exdrf-keep-end more_content -------------------------------------------------
