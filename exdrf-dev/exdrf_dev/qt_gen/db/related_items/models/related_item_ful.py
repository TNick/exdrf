# This file was automatically generated using the exdrf_gen package.
# Source: exdrf_gen_al2qt -> c/m/m_ful.py.j2
# Don't change it manually.

from typing import TYPE_CHECKING

from exdrf_qt.models import QtModel
from sqlalchemy import select

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

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy import Select  # noqa: F401

    from exdrf_dev.db.api import RelatedItem  # noqa: F401


class QtRelatedItemFuMo(QtModel["RelatedItem"]):
    """The model that contains all the fields of the RelatedItem table."""

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.db.api import RelatedItem as DbRelatedItem

        super().__init__(
            ctx=ctx,
            db_model=DbRelatedItem,
            selection=select(DbRelatedItem),
            fields=[
                CompKeyOwnerField,  # type: ignore
                CompKeyPart1Field,  # type: ignore
                CompKeyPart2Field,  # type: ignore
                IdField,  # type: ignore
                ItemDataField,  # type: ignore
                SomeIntField,  # type: ignore
            ],
            **kwargs,
        )
