# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.

from typing import TYPE_CHECKING

from exdrf_qt.models import QtModel
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from exdrf_dev.qt.related_items.fields.comp_key_owner_field import (
    CompKeyOwnerField,
)
from exdrf_dev.qt.related_items.fields.comp_key_part1_field import (
    CompKeyPart1Field,
)
from exdrf_dev.qt.related_items.fields.comp_key_part2_field import (
    CompKeyPart2Field,
)
from exdrf_dev.qt.related_items.fields.id_field import IdField
from exdrf_dev.qt.related_items.fields.item_data_field import ItemDataField
from exdrf_dev.qt.related_items.fields.some_int_field import SomeIntField

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy import Select  # noqa: F401

    from exdrf_dev.db.models import RelatedItem  # noqa: F401


class QtRelatedItemFuMo(QtModel["RelatedItem"]):
    """The model that contains all the fields of the RelatedItem table."""

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.db.models import CompositeKeyModel as DbCompositeKeyModel
        from exdrf_dev.db.models import RelatedItem as DbRelatedItem

        super().__init__(
            ctx=ctx,
            db_model=DbRelatedItem,
            selection=select(DbRelatedItem).options(
                joinedload(
                    DbRelatedItem.comp_key_owner,
                ).load_only(
                    DbCompositeKeyModel.description,
                    DbCompositeKeyModel.key_part1,
                    DbCompositeKeyModel.key_part2,
                )
            ),
            fields=[
                IdField(resource=self),  # type: ignore
                ItemDataField(resource=self),  # type: ignore
                SomeIntField(resource=self),  # type: ignore
                CompKeyPart1Field(resource=self),  # type: ignore
                CompKeyPart2Field(resource=self),  # type: ignore
                CompKeyOwnerField(resource=self),  # type: ignore
            ],
            **kwargs,
        )
