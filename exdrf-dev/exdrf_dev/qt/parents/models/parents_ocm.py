# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.

from typing import TYPE_CHECKING, Any, List, Tuple, Type, Union, cast

from exdrf_dev.qt.parents.fields.children_field import ChildrenField
from exdrf_dev.qt.parents.fields.created_at_field import CreatedAtField
from exdrf_dev.qt.parents.fields.id_field import IdField
from exdrf_dev.qt.parents.fields.is_active_field import IsActiveField
from exdrf_dev.qt.parents.fields.name_field import NameField
from exdrf_dev.qt.parents.fields.profile_field import ProfileField
from exdrf_dev.qt.parents.fields.tags_field import TagsField
from exdrf_qt.models import QtModel

if TYPE_CHECKING:
    from sqlalchemy import Select  # noqa: F401

    from exdrf_dev.db.models import Parent  # noqa: F401
    from exdrf_qt.context import QtContext  # noqa: F401
    from exdrf_qt.models.field import QtField  # noqa: F401


class QtParentNaMo(QtModel["Parent"]):
    """The model that contains only the label field of the
    Parent table.
    """

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.db.models import Parent as DbParent

        fields: List[Type["QtField[Any]"]] = [
            IdField,
            NameField,
            CreatedAtField,
            IsActiveField,
            ChildrenField,
            ProfileField,
            TagsField,
        ]
        super().__init__(
            ctx=ctx,
            db_model=DbParent,
            fields=cast(
                List[Union["QtField[Any]", Type["QtField[Any]"]]],
                fields,
            ),
            **kwargs,
        )
        self.column_fields = ["name"]

    def get_db_item_id(self, item: "Parent") -> Union[int, Tuple[int, ...]]:
        return item.id
