# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> c/m/m_ful.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Union

from exdrf.constants import RecIdType
from exdrf_qt.models import QtModel
from exdrf_qt.plugins import exdrf_qt_pm
from exdrf_qt.utils.plugins import safe_hook_call
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from exdrf_dev.qt_gen.db.children.fields.fld_data import DataField
from exdrf_dev.qt_gen.db.children.fields.fld_id import IdField
from exdrf_dev.qt_gen.db.children.fields.fld_parent import ParentField
from exdrf_dev.qt_gen.db.children.fields.fld_parent_id import ParentIdField

# exdrf-keep-start other_imports ----------------------------------------------

# exdrf-keep-end other_imports ------------------------------------------------

if TYPE_CHECKING:
    from exdrf.filter import FilterType  # noqa: F401
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy import Select  # noqa: F401

    from exdrf_dev.db.api import Child  # noqa: F401

# exdrf-keep-start other_globals ----------------------------------------------

# exdrf-keep-end other_globals ------------------------------------------------


def default_child_list_selection():
    from exdrf_dev.db.api import Child as DbChild
    from exdrf_dev.db.api import Parent as DbParent

    return select(DbChild).options(
        joinedload(DbChild.parent).load_only(
            DbParent.id,
            DbParent.name,
        ),
    )


class QtChildFuMo(QtModel["Child"]):
    """The model that contains all the fields of the Child table."""

    # exdrf-keep-start other_attributes ---------------------------------------

    # exdrf-keep-end other_attributes -----------------------------------------

    def __init__(
        self,
        ctx: "QtContext",
        selection: Union["Select", None] = None,
        fields=None,
        **kwargs,
    ):
        from exdrf_dev.db.api import Child as DbChild

        # Use db_model from kwargs if provided (e.g., from clone_me),
        # otherwise calculate it from context overrides
        db_model = kwargs.pop("db_model", None)
        if db_model is None:
            db_model = ctx.get_ovr(
                "exdrf_dev.qt_gen.db.children.ful.model", DbChild
            )

        super().__init__(
            ctx=ctx,
            db_model=db_model,
            selection=(
                selection
                if selection is not None
                else default_child_list_selection()
            ),
            fields=(
                fields
                if fields is not None
                else [
                    IdField,
                    DataField,
                    ParentIdField,
                    ParentField,
                ]
            ),
            **kwargs,
        )

        # Inform plugins that the model has been created.
        hook = getattr(exdrf_qt_pm.hook, "child_fumo_created", None)
        if hook is not None:
            safe_hook_call(hook, model=self)

    def get_primary_columns(self) -> Any:
        return self.db_model.id

    def get_db_item_id(self, item: "Child") -> Union[int, Tuple[int, ...]]:
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
        exact: Optional[bool] = False,
        limit: Optional[str] = None,
    ) -> "FilterType":
        """Convert a text to a filter.

        The function converts a text to a filter. The text is converted to a
        filter using the `simple_search_fields` property.
        """
        filters = super().text_to_filter(text, exact, limit)
        hook = getattr(exdrf_qt_pm.hook, "child_fumo_ttf", None)
        if hook is not None:
            safe_hook_call(
                hook,
                model=self,
                filters=filters,
                text=text,
                exact=exact,
                limit=limit,
            )
        return filters

        # exdrf-keep-start extra_init -----------------------------------------

        # exdrf-keep-end extra_init -------------------------------------------

    # exdrf-keep-start extra_fumo_content -------------------------------------

    # exdrf-keep-end extra_fumo_content ---------------------------------------


# exdrf-keep-start more_content -----------------------------------------------

# exdrf-keep-end more_content -------------------------------------------------
