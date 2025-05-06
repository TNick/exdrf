# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.

from typing import TYPE_CHECKING, Tuple, Union

from exdrf_qt.models import QtModel

from exdrf_dev.qt.children.fields.data_field import DataField
from exdrf_dev.qt.children.fields.id_field import IdField
from exdrf_dev.qt.children.fields.parent_field import ParentField
from exdrf_dev.qt.children.fields.parent_id_field import ParentIdField

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy import Select  # noqa: F401

    from exdrf_dev.db.models import Child  # noqa: F401


class QtChildNaMo(QtModel["Child"]):
    """The model that contains only the label field of the
    Child table.
    """

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.db.models import Child as DbChild

        fields = [
            IdField,
            DataField,
            ParentIdField,
            ParentField,
        ]
        super().__init__(ctx=ctx, db_model=DbChild, fields=fields, **kwargs)
        self.column_fields = ["data"]

    def get_db_item_id(self, item: "Child") -> Union[int, Tuple[int, ...]]:
        return item.id
