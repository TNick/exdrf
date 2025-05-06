# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.

from typing import TYPE_CHECKING

from exdrf_qt.models import QtModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from exdrf_dev.qt.composite_key_models.fields.description_field import (
    DescriptionField,
)
from exdrf_dev.qt.composite_key_models.fields.key_part1_field import (
    KeyPart1Field,
)
from exdrf_dev.qt.composite_key_models.fields.key_part2_field import (
    KeyPart2Field,
)
from exdrf_dev.qt.composite_key_models.fields.related_items_field import (
    RelatedItemsField,
)
from exdrf_dev.qt.composite_key_models.fields.some_binary_field import (
    SomeBinaryField,
)
from exdrf_dev.qt.composite_key_models.fields.some_date_field import (
    SomeDateField,
)
from exdrf_dev.qt.composite_key_models.fields.some_enum_field import (
    SomeEnumField,
)
from exdrf_dev.qt.composite_key_models.fields.some_float_field import (
    SomeFloatField,
)
from exdrf_dev.qt.composite_key_models.fields.some_json_field import (
    SomeJsonField,
)
from exdrf_dev.qt.composite_key_models.fields.some_time_field import (
    SomeTimeField,
)

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy import Select  # noqa: F401

    from exdrf_dev.db.models import CompositeKeyModel  # noqa: F401


class QtCompositeKeyModelFuMo(QtModel["CompositeKeyModel"]):
    """The model that contains all the fields of the CompositeKeyModel table."""

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.db.models import CompositeKeyModel as DbCompositeKeyModel
        from exdrf_dev.db.models import RelatedItem as DbRelatedItem

        super().__init__(
            ctx=ctx,
            db_model=DbCompositeKeyModel,
            selection=select(DbCompositeKeyModel).options(
                selectinload(
                    DbCompositeKeyModel.related_items,
                ).load_only(
                    DbRelatedItem.id,
                )
            ),
            fields=[
                KeyPart1Field,
                KeyPart2Field,
                DescriptionField,
                SomeFloatField,
                SomeDateField,
                SomeTimeField,
                SomeEnumField,
                SomeJsonField,
                SomeBinaryField,
                RelatedItemsField,
            ],
            **kwargs,
        )
