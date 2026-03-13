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
from sqlalchemy.orm import selectinload

from exdrf_dev.qt_gen.db.composite_key_models.fields.fld_description import (
    DescriptionField,
)
from exdrf_dev.qt_gen.db.composite_key_models.fields.fld_key_part1 import (
    KeyPart1Field,
)
from exdrf_dev.qt_gen.db.composite_key_models.fields.fld_key_part2 import (
    KeyPart2Field,
)
from exdrf_dev.qt_gen.db.composite_key_models.fields.fld_related_items import (
    RelatedItemsField,
)
from exdrf_dev.qt_gen.db.composite_key_models.fields.fld_some_binary import (
    SomeBinaryField,
)
from exdrf_dev.qt_gen.db.composite_key_models.fields.fld_some_date import (
    SomeDateField,
)
from exdrf_dev.qt_gen.db.composite_key_models.fields.fld_some_enum import (
    SomeEnumField,
)
from exdrf_dev.qt_gen.db.composite_key_models.fields.fld_some_float import (
    SomeFloatField,
)
from exdrf_dev.qt_gen.db.composite_key_models.fields.fld_some_json import (
    SomeJsonField,
)
from exdrf_dev.qt_gen.db.composite_key_models.fields.fld_some_time import (
    SomeTimeField,
)

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf.filter import FilterType  # noqa: F401
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy import Select  # noqa: F401

    from exdrf_dev.db.api import CompositeKeyModel  # noqa: F401

# exdrf-keep-start other_globals ----------------------------------------------

# exdrf-keep-end other_globals ------------------------------------------------


@lru_cache(maxsize=1)
def _default_composite_key_model_list_selection_base():
    from exdrf_dev.db.api import CompositeKeyModel as DbCompositeKeyModel
    from exdrf_dev.db.api import RelatedItem as DbRelatedItem

    try:
        return select(DbCompositeKeyModel).options(
            selectinload(
                DbCompositeKeyModel.related_items,
            ).load_only(
                DbRelatedItem.id,
            ),
        )
    except Exception:
        logging.getLogger(__name__).error(
            "Error creating default selection for composite_key_model",
            exc_info=True,
        )
        return select(DbCompositeKeyModel)


def default_composite_key_model_list_selection(db_model: Any):
    from exdrf_dev.db.api import CompositeKeyModel as DbCompositeKeyModel

    # If an override changes the ORM model class, the statically generated
    # eager-loading options will not match. Fall back to a plain select on the
    # overridden model to keep the query valid on all dialects.
    if db_model is not DbCompositeKeyModel:
        return select(db_model)

    return _default_composite_key_model_list_selection_base()


class QtCompositeKeyModelFuMo(QtModel["CompositeKeyModel"]):
    """The model that contains all the fields of the CompositeKeyModel table."""

    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------

    def __init__(
        self,
        ctx: "QtContext",
        selection: Union["Select", None] = None,
        fields=None,
        **kwargs,
    ):
        from exdrf_dev.db.api import CompositeKeyModel as DbCompositeKeyModel

        # Use db_model from kwargs if provided (e.g., from clone_me),
        # otherwise calculate it from context overrides
        db_model = kwargs.pop("db_model", None)
        if db_model is None:
            db_model = ctx.get_ovr(
                "exdrf_dev.qt_gen.db.composite_key_models.ful.model",
                DbCompositeKeyModel,
            )

        super().__init__(
            ctx=ctx,
            db_model=db_model,
            selection=(
                selection
                if selection is not None
                else default_composite_key_model_list_selection(db_model)
            ),
            fields=(
                fields
                if fields is not None
                else [
                    DescriptionField,
                    SomeBinaryField,
                    SomeDateField,
                    SomeEnumField,
                    SomeFloatField,
                    SomeJsonField,
                    SomeTimeField,
                    RelatedItemsField,
                    KeyPart1Field,
                    KeyPart2Field,
                ]
            ),
            **kwargs,
        )

        # The fields that are visible in the UI. Excluded from here are
        # the the foreign key fields that are already represented by
        # a resource field and derived fields (e.g. diacritic-less values):
        # - some_binary
        self.column_fields = [
            "description",
            "some_date",
            "some_enum",
            "some_float",
            "some_json",
            "some_time",
            "related_items",
            "key_part1",
            "key_part2",
        ]

        # Inform plugins that the model has been created.
        safe_hook_call(
            exdrf_qt_pm.hook.composite_key_model_fumo_created, model=self
        )

    def get_primary_columns(self) -> Any:
        return [
            self.db_model.key_part1,
            self.db_model.key_part2,
        ]

    def get_db_item_id(
        self, item: "CompositeKeyModel"
    ) -> Union[int, Tuple[int, ...]]:
        return (
            item.key_part1,
            item.key_part2,
        )

    def item_by_id_conditions(self, rec_id: RecIdType) -> List[Any]:
        """Return the conditions that filter by ID.

        Args:
            rec_id: The ID of the item to filter by.
        """
        assert 2 == len(rec_id), (
            "ID tuple does not match the number of primary keys. "
            f"Model: {self.db_model.__name__} "
            f"ID: {rec_id}/{rec_id.__class__.__name__}"
        )
        return [
            self.db_model.key_part1 == rec_id[0],
            self.db_model.key_part2 == rec_id[1],
        ]

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
            exdrf_qt_pm.hook.composite_key_model_fumo_ttf,
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
