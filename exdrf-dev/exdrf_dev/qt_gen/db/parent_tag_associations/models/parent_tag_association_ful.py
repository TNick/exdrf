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

from exdrf_dev.qt_gen.db.parent_tag_associations.fields.fld_parent_id import (
    ParentIdField,
)
from exdrf_dev.qt_gen.db.parent_tag_associations.fields.fld_tag_id import (
    TagIdField,
)

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf.filter import FilterType  # noqa: F401
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy import Select  # noqa: F401

    from exdrf_dev.db.api import ParentTagAssociation  # noqa: F401

# exdrf-keep-start other_globals ----------------------------------------------

# exdrf-keep-end other_globals ------------------------------------------------


@lru_cache(maxsize=1)
def _default_parent_tag_association_list_selection_base():
    from exdrf_dev.db.api import ParentTagAssociation as DbParentTagAssociation

    try:
        return select(DbParentTagAssociation)
    except Exception:
        logging.getLogger(__name__).error(
            "Error creating default selection for parent_tag_association",
            exc_info=True,
        )
        return select(DbParentTagAssociation)


def default_parent_tag_association_list_selection(db_model: Any):
    from exdrf_dev.db.api import ParentTagAssociation as DbParentTagAssociation

    # If an override changes the ORM model class, the statically generated
    # eager-loading options will not match. Fall back to a plain select on the
    # overridden model to keep the query valid on all dialects.
    if db_model is not DbParentTagAssociation:
        return select(db_model)

    return _default_parent_tag_association_list_selection_base()


class QtParentTagAssociationFuMo(QtModel["ParentTagAssociation"]):
    """The model that contains all the fields of the ParentTagAssociation table."""

    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------

    def __init__(
        self,
        ctx: "QtContext",
        selection: Union["Select", None] = None,
        fields=None,
        **kwargs,
    ):
        from exdrf_dev.db.api import (
            ParentTagAssociation as DbParentTagAssociation,
        )

        # Use db_model from kwargs if provided (e.g., from clone_me),
        # otherwise calculate it from context overrides
        db_model = kwargs.pop("db_model", None)
        if db_model is None:
            db_model = ctx.get_ovr(
                "exdrf_dev.qt_gen.db.parent_tag_associations.ful.model",
                DbParentTagAssociation,
            )

        super().__init__(
            ctx=ctx,
            db_model=db_model,
            selection=(
                selection
                if selection is not None
                else default_parent_tag_association_list_selection(db_model)
            ),
            fields=(
                fields
                if fields is not None
                else [
                    ParentIdField,
                    TagIdField,
                ]
            ),
            **kwargs,
        )

        # The fields that are visible in the UI. Excluded from here are
        # the the foreign key fields that are already represented by
        # a resource field and derived fields (e.g. diacritic-less values):
        self.column_fields = [
            "parent_id",
            "tag_id",
        ]

        # Inform plugins that the model has been created.
        safe_hook_call(
            exdrf_qt_pm.hook.parent_tag_association_fumo_created, model=self
        )

    def get_primary_columns(self) -> Any:
        return [
            self.db_model.parent_id,
            self.db_model.tag_id,
        ]

    def get_db_item_id(
        self, item: "ParentTagAssociation"
    ) -> Union[int, Tuple[int, ...]]:
        return (
            item.parent_id,
            item.tag_id,
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
            self.db_model.parent_id == rec_id[0],
            self.db_model.tag_id == rec_id[1],
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
            exdrf_qt_pm.hook.parent_tag_association_fumo_ttf,
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
