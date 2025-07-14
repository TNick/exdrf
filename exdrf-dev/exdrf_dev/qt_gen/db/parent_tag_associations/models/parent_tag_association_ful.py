# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> c/m/m_ful.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Union

from exdrf.constants import RecIdType
from exdrf_qt.models import QtModel
from exdrf_qt.plugins import exdrf_qt_pm, safe_hook_call
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


def default_parent_tag_association_list_selection():
    from exdrf_dev.db.api import ParentTagAssociation as DbParentTagAssociation

    return select(DbParentTagAssociation)


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

        super().__init__(
            ctx=ctx,
            db_model=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.parent_tag_associations.ful.model",
                DbParentTagAssociation,
            ),
            selection=(
                selection
                if selection is not None
                else default_parent_tag_association_list_selection()
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
        return [
            item.parent_id,
            item.tag_id,
        ]

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
        exact: Optional[bool] = False,
        limit: Optional[str] = None,
    ) -> "FilterType":
        """Convert a text to a filter.

        The function converts a text to a filter. The text is converted to a
        filter using the `simple_search_fields` property.
        """
        filters = super().text_to_filter(text, exact, limit)
        safe_hook_call(
            exdrf_qt_pm.hook.parent_tag_association_fumo_ttf, model=self
        )
        return filters

        # exdrf-keep-start extra_init -----------------------------------------

        # exdrf-keep-end extra_init -------------------------------------------

    # exdrf-keep-start extra_fumo_content -------------------------------------

    # exdrf-keep-end extra_fumo_content ---------------------------------------


# exdrf-keep-start more_content -----------------------------------------------

# exdrf-keep-end more_content -------------------------------------------------
