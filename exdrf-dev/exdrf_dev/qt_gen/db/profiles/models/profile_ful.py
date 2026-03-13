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

from exdrf_dev.qt_gen.db.profiles.fields.fld_bio import BioField
from exdrf_dev.qt_gen.db.profiles.fields.fld_id import IdField
from exdrf_dev.qt_gen.db.profiles.fields.fld_parent import ParentField
from exdrf_dev.qt_gen.db.profiles.fields.fld_parent_id import ParentIdField

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf.filter import FilterType  # noqa: F401
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy import Select  # noqa: F401

    from exdrf_dev.db.api import Profile  # noqa: F401

# exdrf-keep-start other_globals ----------------------------------------------

# exdrf-keep-end other_globals ------------------------------------------------


@lru_cache(maxsize=1)
def _default_profile_list_selection_base():
    from exdrf_dev.db.api import Parent as DbParent
    from exdrf_dev.db.api import Profile as DbProfile

    try:
        return select(DbProfile).options(
            joinedload(
                DbProfile.parent,
            ).load_only(
                DbParent.id,
                DbParent.name,
            ),
        )
    except Exception:
        logging.getLogger(__name__).error(
            "Error creating default selection for profile",
            exc_info=True,
        )
        return select(DbProfile)


def default_profile_list_selection(db_model: Any):
    from exdrf_dev.db.api import Profile as DbProfile

    # If an override changes the ORM model class, the statically generated
    # eager-loading options will not match. Fall back to a plain select on the
    # overridden model to keep the query valid on all dialects.
    if db_model is not DbProfile:
        return select(db_model)

    return _default_profile_list_selection_base()


class QtProfileFuMo(QtModel["Profile"]):
    """The model that contains all the fields of the Profile table."""

    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------

    def __init__(
        self,
        ctx: "QtContext",
        selection: Union["Select", None] = None,
        fields=None,
        **kwargs,
    ):
        from exdrf_dev.db.api import Profile as DbProfile

        # Use db_model from kwargs if provided (e.g., from clone_me),
        # otherwise calculate it from context overrides
        db_model = kwargs.pop("db_model", None)
        if db_model is None:
            db_model = ctx.get_ovr(
                "exdrf_dev.qt_gen.db.profiles.ful.model", DbProfile
            )

        super().__init__(
            ctx=ctx,
            db_model=db_model,
            selection=(
                selection
                if selection is not None
                else default_profile_list_selection(db_model)
            ),
            fields=(
                fields
                if fields is not None
                else [
                    BioField,
                    ParentField,
                    ParentIdField,
                    IdField,
                ]
            ),
            **kwargs,
        )

        # The fields that are visible in the UI. Excluded from here are
        # the the foreign key fields that are already represented by
        # a resource field and derived fields (e.g. diacritic-less values):
        # - parent_id
        self.column_fields = [
            "bio",
            "parent",
            "id",
        ]

        # Inform plugins that the model has been created.
        safe_hook_call(exdrf_qt_pm.hook.profile_fumo_created, model=self)

    def get_primary_columns(self) -> Any:
        return self.db_model.id

    def get_db_item_id(self, item: "Profile") -> Union[int, Tuple[int, ...]]:
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
            exdrf_qt_pm.hook.profile_fumo_ttf,
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
