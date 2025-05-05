# This file was automatically generated using a proprietary package.
# Source: db2qt.database_to_qt
# Don't change it manually.

from typing import TYPE_CHECKING, Tuple, Union

from exdrf_qt.models import QtModel

from exdrf_dev.qt.parents.fields.children_field import ChildrenField
from exdrf_dev.qt.parents.fields.created_at_field import CreatedAtField
from exdrf_dev.qt.parents.fields.id_field import IdField
from exdrf_dev.qt.parents.fields.is_active_field import IsActiveField
from exdrf_dev.qt.parents.fields.name_field import NameField
from exdrf_dev.qt.parents.fields.profile_field import ProfileField
from exdrf_dev.qt.parents.fields.tags_field import TagsField

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401
    from sqlalchemy import Select  # noqa: F401

    from exdrf_dev.db.models import Parent  # noqa: F401


class QtParentNaMo(QtModel["Parent"]):
    """The model that contains only the label field of the
    Parent table.
    """

    def __init__(self, ctx: "QtContext", **kwargs):
        from exdrf_dev.db.models import Parent as DbParent

        fields = [
            IdField(resource=self),  # type: ignore
            NameField(resource=self),  # type: ignore
            CreatedAtField(resource=self),  # type: ignore
            IsActiveField(resource=self),  # type: ignore
            ChildrenField(resource=self),  # type: ignore
            ProfileField(resource=self),  # type: ignore
            TagsField(resource=self),  # type: ignore
        ]
        super().__init__(
            ctx=ctx,
            db_model=DbParent,
            fields=fields,
            **kwargs,
        )
        self.column_fields = [fields[1].name]

    def get_db_item_id(self, item: "Parent") -> Union[int, Tuple[int, ...]]:
        return item.id
