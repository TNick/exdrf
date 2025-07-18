# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt.creator -> c/m/m_ful.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING, Optional, Union

from exdrf_qt.models import QtModel
from exdrf_qt.plugins import exdrf_qt_pm, safe_hook_call
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


def default_composite_key_model_list_selection():
    from exdrf_dev.db.api import CompositeKeyModel as DbCompositeKeyModel
    from exdrf_dev.db.api import RelatedItem as DbRelatedItem

    return select(DbCompositeKeyModel).options(
        selectinload(DbCompositeKeyModel.related_items).load_only(
            DbRelatedItem.id,
        ),
    )


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

        super().__init__(
            ctx=ctx,
            db_model=ctx.get_ovr(
                "exdrf_dev.qt_gen.db.composite_key_models.ful.model",
                DbCompositeKeyModel,
            ),
            selection=(
                selection
                if selection is not None
                else default_composite_key_model_list_selection()
            ),
            fields=(
                fields
                if fields is not None
                else [
                    DescriptionField,
                    RelatedItemsField,
                    SomeBinaryField,
                    SomeDateField,
                    SomeEnumField,
                    SomeFloatField,
                    SomeJsonField,
                    SomeTimeField,
                    KeyPart1Field,
                    KeyPart2Field,
                ]
            ),
            **kwargs,
        )

        # Inform plugins that the model has been created.
        safe_hook_call(
            exdrf_qt_pm.hook.composite_key_model_fumo_created, model=self
        )

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
            exdrf_qt_pm.hook.composite_key_model_fumo_ttf, model=self
        )
        return filters

        # exdrf-keep-start extra_init -----------------------------------------

        # exdrf-keep-end extra_init -------------------------------------------

    # exdrf-keep-start extra_fumo_content -------------------------------------

    # exdrf-keep-end extra_fumo_content ---------------------------------------


# exdrf-keep-start more_content -----------------------------------------------

# exdrf-keep-end more_content -------------------------------------------------
